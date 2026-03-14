"""LLM-based virality scoring of transcript segments."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


@dataclass
class ScoredSegment:
    """A transcript segment with a virality score."""

    start: float
    end: float
    text: str
    score: float  # 0.0 - 10.0
    reasoning: str
    hook_suggestion: str
    tags: list[str]


SCORING_PROMPT = """\
You are a short-form content strategist. Your job is to analyze transcript segments \
from podcasts and videos and score them by their potential to go viral on TikTok, \
Instagram Reels, and YouTube Shorts.

Score each segment from 0 to 10 based on these criteria:
- **Controversy / Hot Take** (2 pts): Does it contain a polarizing opinion that would \
spark comments?
- **Emotional Impact** (2 pts): Does it evoke strong emotions (shock, inspiration, \
humor, anger)?
- **Quotability** (2 pts): Is there a memorable, shareable one-liner or statement?
- **Story / Narrative Hook** (2 pts): Does it tell a compelling mini-story or reveal?
- **Relatability** (2 pts): Would a wide audience see themselves in this?

For each segment, return a JSON object with:
- "score": number (0-10)
- "reasoning": brief explanation of the score
- "hook_suggestion": a 5-8 word text hook to overlay in the first 2 seconds
- "tags": list of content category tags (e.g., "motivation", "dating", "business", "funny")

Analyze these segments and return a JSON array of results, one per segment, in the same order:

{segments}
"""


def _build_segments_text(segments: list[dict]) -> str:
    """Format segments for the scoring prompt."""
    parts = []
    for i, seg in enumerate(segments):
        parts.append(f"--- Segment {i + 1} (time: {seg['start']:.1f}s - {seg['end']:.1f}s) ---")
        parts.append(seg["text"])
        parts.append("")
    return "\n".join(parts)


def _extract_json_array(text: str) -> list[dict]:
    """Extract a JSON array from LLM response text, handling markdown fences."""
    # Try direct parse first
    text = text.strip()
    if text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try extracting from markdown code fences
    match = re.search(r"```(?:json)?\s*(\[.*?])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding any JSON array in the text
    match = re.search(r"\[.*]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON array from LLM response: {text[:200]}...")


def score_segments(
    segments: list[dict],
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    min_score: float = 6.0,
) -> list[ScoredSegment]:
    """Score transcript segments using Claude API.

    Args:
        segments: List of dicts with 'start', 'end', 'text' keys.
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        model: Claude model to use.
        min_score: Minimum score threshold to include in results.

    Returns:
        List of ScoredSegment objects, sorted by score descending,
        filtered to min_score threshold.
    """
    import anthropic

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key parameter."
        )

    client = anthropic.Anthropic(api_key=api_key)

    segments_text = _build_segments_text(segments)
    prompt = SCORING_PROMPT.format(segments=segments_text)

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    results = _extract_json_array(response_text)

    scored = []
    for seg, result in zip(segments, results):
        score = float(result.get("score", 0))
        scored.append(
            ScoredSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                score=score,
                reasoning=result.get("reasoning", ""),
                hook_suggestion=result.get("hook_suggestion", ""),
                tags=result.get("tags", []),
            )
        )

    # Filter and sort
    scored = [s for s in scored if s.score >= min_score]
    scored.sort(key=lambda s: s.score, reverse=True)

    return scored


def segment_transcript(
    transcript_data: dict,
    window_seconds: float = 60.0,
    overlap_seconds: float = 15.0,
    min_words: int = 30,
) -> list[dict]:
    """Split a transcript into overlapping candidate windows for scoring.

    Args:
        transcript_data: Parsed transcript JSON from Whisper.
        window_seconds: Target window duration in seconds.
        overlap_seconds: Overlap between consecutive windows.
        min_words: Minimum word count for a window to be considered.

    Returns:
        List of dicts with 'start', 'end', 'text' keys.
    """
    segments = transcript_data.get("segments", [])
    if not segments:
        return []

    total_duration = segments[-1]["end"]
    step = window_seconds - overlap_seconds
    windows = []

    start = 0.0
    while start < total_duration:
        end = min(start + window_seconds, total_duration)

        # Collect text from segments that fall within this window
        window_text_parts = []
        for seg in segments:
            # Include segment if it overlaps with the window
            if seg["end"] > start and seg["start"] < end:
                window_text_parts.append(seg["text"])

        text = " ".join(window_text_parts).strip()
        word_count = len(text.split())

        if word_count >= min_words:
            windows.append({"start": start, "end": end, "text": text})

        start += step
        if end >= total_duration:
            break

    return windows
