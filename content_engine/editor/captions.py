"""Animated word-by-word caption generation.

Generates ASS (Advanced SubStation Alpha) subtitles from Whisper word-level
timestamps with TikTok-style word highlighting, then burns them into the
video via FFmpeg.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CaptionStyle:
    """Visual style for captions."""

    font_name: str = "Arial"
    font_size: int = 20
    primary_color: str = "&H00FFFFFF"  # white (ASS BGR format)
    highlight_color: str = "&H0000FFFF"  # yellow highlight for active word
    outline_color: str = "&H00000000"  # black outline
    back_color: str = "&H80000000"  # semi-transparent black background
    outline_width: int = 2
    shadow: int = 0
    margin_v: int = 40  # vertical margin from bottom
    alignment: int = 2  # bottom-center (ASS alignment)
    bold: bool = True
    uppercase: bool = True
    words_per_group: int = 4  # words shown simultaneously


@dataclass
class WordTimestamp:
    """A single word with its timing."""

    word: str
    start: float
    end: float


def load_word_timestamps(transcript_path: str, clip_start: float = 0.0, clip_end: float | None = None) -> list[WordTimestamp]:
    """Load word-level timestamps from a Whisper transcript JSON.

    Args:
        transcript_path: Path to the transcript JSON file.
        clip_start: Start time of the clip (to offset timestamps).
        clip_end: End time of the clip (to filter words).

    Returns:
        List of WordTimestamp objects with times relative to clip start.
    """
    with open(transcript_path) as f:
        data = json.load(f)

    words = []
    for segment in data.get("segments", []):
        for w in segment.get("words", []):
            abs_start = w["start"]
            abs_end = w["end"]

            # Filter to clip range
            if clip_end is not None and abs_start >= clip_end:
                break
            if abs_end <= clip_start:
                continue

            words.append(WordTimestamp(
                word=w["word"].strip(),
                start=max(0, abs_start - clip_start),
                end=abs_end - clip_start,
            ))

    return words


def _format_ass_time(seconds: float) -> str:
    """Format seconds to ASS timestamp (H:MM:SS.cc)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_color(color_str: str) -> str:
    """Ensure ASS color format."""
    return color_str


def generate_ass_subtitles(
    words: list[WordTimestamp],
    style: CaptionStyle | None = None,
    video_width: int = 1080,
    video_height: int = 1920,
) -> str:
    """Generate ASS subtitle content with word-by-word highlighting.

    Groups words into chunks and highlights the active word within each
    group as it's spoken — the signature TikTok caption style.

    Args:
        words: Word timestamps from Whisper.
        style: Caption styling options.
        video_width: Target video width (for layout).
        video_height: Target video height (for layout).

    Returns:
        Complete ASS subtitle file content as a string.
    """
    if style is None:
        style = CaptionStyle()

    if not words:
        return ""

    # ASS header
    header = f"""[Script Info]
Title: Content Engine Captions
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{style.primary_color},{style.highlight_color},{style.outline_color},{style.back_color},{int(style.bold)},0,0,0,100,100,0,0,1,{style.outline_width},{style.shadow},{style.alignment},20,20,{style.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = [header.strip()]

    # Group words into display chunks
    n = style.words_per_group
    groups = [words[i : i + n] for i in range(0, len(words), n)]

    for group in groups:
        group_start = group[0].start
        group_end = group[-1].end

        # Build the dialogue line with per-word highlight timing
        # Each word gets a karaoke timing tag so it highlights when spoken
        text_parts = []
        for w in group:
            word_text = w.word.upper() if style.uppercase else w.word
            # Duration of this word in centiseconds for karaoke timing
            dur_cs = int((w.end - w.start) * 100)
            # \kf = smooth fill karaoke effect
            text_parts.append(f"{{\\kf{dur_cs}}}{word_text}")

        text = " ".join(text_parts)

        start_ts = _format_ass_time(group_start)
        end_ts = _format_ass_time(group_end)

        lines.append(
            f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
        )

    return "\n".join(lines) + "\n"


def write_ass_file(ass_content: str, output_path: str) -> str:
    """Write ASS subtitle content to a file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    logger.info("ASS subtitle file written: %s", output_path)
    return output_path


def burn_captions(
    video_path: str,
    ass_path: str,
    output_path: str,
) -> str:
    """Burn ASS subtitles into a video using FFmpeg.

    Args:
        video_path: Input video path.
        ass_path: ASS subtitle file path.
        output_path: Output video path.

    Returns:
        Path to the output video.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Use the ass filter (more feature-rich than subtitles filter)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"ass='{ass_path}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: try subtitles filter which handles paths differently
        logger.warning("ass filter failed, trying subtitles filter: %s", result.stderr[:200])
        cmd_fallback = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{ass_path}'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
        subprocess.run(cmd_fallback, capture_output=True, text=True, check=True)

    logger.info("Captions burned into video: %s", output_path)
    return output_path


def generate_captions_for_clip(
    transcript_path: str,
    clip_start: float,
    clip_end: float,
    output_ass_path: str,
    style: CaptionStyle | None = None,
    video_width: int = 1080,
    video_height: int = 1920,
) -> str:
    """End-to-end: load transcript, generate ASS, write file.

    Args:
        transcript_path: Path to Whisper transcript JSON.
        clip_start: Clip start time in the source.
        clip_end: Clip end time in the source.
        output_ass_path: Where to write the ASS file.
        style: Caption styling.
        video_width: Target video width.
        video_height: Target video height.

    Returns:
        Path to the generated ASS file.
    """
    words = load_word_timestamps(transcript_path, clip_start, clip_end)
    if not words:
        logger.warning("No word timestamps found for clip range %.1f-%.1f", clip_start, clip_end)
        return ""

    ass_content = generate_ass_subtitles(words, style, video_width, video_height)
    return write_ass_file(ass_content, output_ass_path)
