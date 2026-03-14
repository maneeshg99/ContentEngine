"""Automated clip selection pipeline — transcribe, score, select, cut."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from content_engine.clipper.audio_analysis import get_energy_peaks
from content_engine.clipper.cutter import extract_clip
from content_engine.clipper.scorer import ScoredSegment, score_segments, segment_transcript
from content_engine.clipper.transcriber import transcribe_source
from content_engine.config import AppConfig
from content_engine.database import Clip, ClipStatus, Source, SourceStatus


def auto_clip(
    source: Source,
    config: AppConfig,
    session,
    top_n: int = 5,
    min_score: float = 6.0,
    api_key: str | None = None,
    use_energy: bool = True,
    energy_weight: float = 0.2,
) -> list[Clip]:
    """Full automated pipeline: transcribe → score → select → cut.

    Args:
        source: Source record (must be at least DOWNLOADED).
        config: App configuration.
        session: Database session.
        top_n: Number of top clips to extract.
        min_score: Minimum virality score threshold.
        api_key: Anthropic API key (falls back to env var).
        use_energy: Whether to incorporate audio energy analysis.
        energy_weight: How much audio energy influences the final score (0-1).

    Returns:
        List of created Clip records.
    """
    # Step 1: Transcribe if needed
    if source.status == SourceStatus.DOWNLOADED:
        transcribe_source(source, config, session)
    elif source.status.value in ("pending", "downloading"):
        raise ValueError(f"Source must be downloaded first. Status: {source.status.value}")

    # Step 2: Load transcript
    transcript_path = source.transcript_path
    if not transcript_path or not Path(transcript_path).exists():
        raise FileNotFoundError(f"Transcript not found at {transcript_path}")

    with open(transcript_path) as f:
        transcript_data = json.load(f)

    # Step 3: Segment transcript into candidate windows
    windows = segment_transcript(
        transcript_data,
        window_seconds=float(config.clipper.max_duration),
        overlap_seconds=15.0,
    )

    if not windows:
        return []

    # Step 4: Score segments with LLM
    scored_segments = score_segments(
        windows,
        api_key=api_key,
        min_score=min_score,
    )

    # Step 5: Optionally blend in audio energy
    if use_energy and scored_segments:
        scored_segments = _blend_energy_scores(
            source.file_path, scored_segments, energy_weight
        )

    # Step 6: Deduplicate overlapping segments, keeping higher scores
    scored_segments = _deduplicate_segments(scored_segments, min_gap=10.0)

    # Step 7: Take top N and extract clips
    top_segments = scored_segments[:top_n]
    clips = []

    for seg in top_segments:
        # Adjust to config bounds
        duration = seg.end - seg.start
        if duration < config.clipper.min_duration:
            # Extend symmetrically
            pad = (config.clipper.min_duration - duration) / 2
            seg_start = max(0, seg.start - pad)
            seg_end = seg.end + pad
        elif duration > config.clipper.max_duration:
            seg_end = seg.start + config.clipper.max_duration
            seg_start = seg.start
        else:
            seg_start = seg.start
            seg_end = seg.end

        try:
            clip = extract_clip(
                source, seg_start, seg_end, config, session,
                title=seg.hook_suggestion,
            )
            # Store scoring metadata on the clip
            clip.virality_score = seg.score
            clip.transcript_segment = seg.text[:2000]  # Truncate for DB
            session.commit()
            clips.append(clip)
        except (ValueError, RuntimeError) as e:
            # Log but don't fail the whole pipeline
            print(f"Warning: skipping segment {seg.start:.1f}-{seg.end:.1f}: {e}")
            continue

    # Update source status
    source.status = SourceStatus.CLIPPED
    session.commit()

    return clips


def _blend_energy_scores(
    file_path: str,
    segments: list[ScoredSegment],
    energy_weight: float,
) -> list[ScoredSegment]:
    """Blend audio energy analysis into virality scores.

    Segments that align with audio energy peaks get a score boost.
    """
    peaks = get_energy_peaks(file_path, window_seconds=5.0, top_n=50)
    if not peaks:
        return segments

    # Normalize energy values to 0-10 scale
    max_energy = max(p["energy"] for p in peaks)
    if max_energy == 0:
        return segments

    for seg in segments:
        # Find average energy of peaks within this segment's time range
        overlapping = [
            p for p in peaks
            if p["start"] < seg.end and p["end"] > seg.start
        ]
        if overlapping:
            avg_energy = sum(p["energy"] for p in overlapping) / len(overlapping)
            normalized_energy = (avg_energy / max_energy) * 10.0
            # Blend: (1 - weight) * llm_score + weight * energy_score
            seg.score = (1 - energy_weight) * seg.score + energy_weight * normalized_energy

    # Re-sort after blending
    segments.sort(key=lambda s: s.score, reverse=True)
    return segments


def _deduplicate_segments(
    segments: list[ScoredSegment],
    min_gap: float = 10.0,
) -> list[ScoredSegment]:
    """Remove overlapping segments, keeping the higher-scored one.

    Args:
        segments: Scored segments sorted by score descending.
        min_gap: Minimum gap in seconds between kept segments.
    """
    kept = []
    for seg in segments:
        overlaps = False
        for existing in kept:
            # Check if segments overlap (with min_gap buffer)
            if seg.start < existing.end + min_gap and seg.end > existing.start - min_gap:
                overlaps = True
                break
        if not overlaps:
            kept.append(seg)
    return kept
