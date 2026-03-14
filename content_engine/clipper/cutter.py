"""FFmpeg-based clip extraction."""

from __future__ import annotations

import subprocess
from pathlib import Path

from content_engine.config import AppConfig
from content_engine.database import Clip, ClipStatus, Source


def extract_clip(
    source: Source,
    start_time: float,
    end_time: float,
    config: AppConfig,
    session,
    title: str | None = None,
) -> Clip:
    """Extract a clip from a source video using FFmpeg.

    Args:
        source: The source record to clip from.
        start_time: Start time in seconds.
        end_time: End time in seconds.
        config: App configuration.
        session: Database session.
        title: Optional clip title.

    Returns:
        The created Clip record.
    """
    clips_dir = Path(config.storage.clips_dir)
    clips_dir.mkdir(parents=True, exist_ok=True)

    duration = end_time - start_time
    if duration < config.clipper.min_duration:
        raise ValueError(
            f"Clip duration {duration:.1f}s is below minimum {config.clipper.min_duration}s"
        )
    if duration > config.clipper.max_duration:
        raise ValueError(
            f"Clip duration {duration:.1f}s exceeds maximum {config.clipper.max_duration}s"
        )

    # Generate output filename
    source_stem = Path(source.file_path).stem
    clip_filename = f"{source_stem}_clip_{start_time:.0f}_{end_time:.0f}.mp4"
    output_path = clips_dir / clip_filename

    # FFmpeg command: re-encode for compatibility across platforms
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-i", source.file_path,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, text=True, check=True)

    # Create clip record
    clip_record = Clip(
        source_id=source.id,
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        file_path=str(output_path),
        title=title,
        status=ClipStatus.EXTRACTED,
    )
    session.add(clip_record)
    session.commit()
    session.refresh(clip_record)

    return clip_record
