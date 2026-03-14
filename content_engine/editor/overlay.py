"""Text hook overlays and branding.

Adds text hooks (e.g. "Wait for it...", "This changed everything") in the
first few seconds of a clip, plus optional logo/watermark placement.
All done via FFmpeg filters for speed and quality.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HookStyle:
    """Style for text hook overlays."""

    font: str = "Arial"
    font_size: int = 56
    font_color: str = "white"
    border_color: str = "black"
    border_width: int = 3
    position_x: str = "(w-text_w)/2"  # centered
    position_y: str = "h*0.15"  # 15% from top
    fade_in: float = 0.3  # seconds
    fade_out: float = 0.3  # seconds
    duration: float = 2.5  # total display time in seconds
    start_time: float = 0.3  # delay before showing
    shadow_color: str = "black@0.5"
    shadow_x: int = 2
    shadow_y: int = 2


@dataclass
class WatermarkConfig:
    """Configuration for logo/watermark overlay."""

    image_path: str = ""
    position: str = "top-right"  # top-left, top-right, bottom-left, bottom-right
    opacity: float = 0.7
    scale: float = 0.08  # fraction of video width
    margin: int = 20


def build_hook_filter(text: str, style: HookStyle | None = None) -> str:
    """Build an FFmpeg drawtext filter string for a text hook overlay.

    Args:
        text: The hook text to display.
        style: Visual style options.

    Returns:
        FFmpeg filter string for the drawtext filter.
    """
    if style is None:
        style = HookStyle()

    # Escape special characters for FFmpeg drawtext
    escaped = (
        text.replace("\\", "\\\\")
        .replace("'", "\u2019")  # smart quote to avoid shell issues
        .replace(":", "\\:")
        .replace("%", "%%")
    )

    start = style.start_time
    end = start + style.duration
    fade_in_end = start + style.fade_in
    fade_out_start = end - style.fade_out

    # Alpha expression for fade in/out
    alpha = (
        f"if(lt(t,{start}),0,"
        f"if(lt(t,{fade_in_end}),(t-{start})/{style.fade_in},"
        f"if(lt(t,{fade_out_start}),1,"
        f"if(lt(t,{end}),({end}-t)/{style.fade_out},0))))"
    )

    drawtext = (
        f"drawtext=text='{escaped}'"
        f":fontfile=''"
        f":fontsize={style.font_size}"
        f":fontcolor={style.font_color}"
        f":borderw={style.border_width}"
        f":bordercolor={style.border_color}"
        f":shadowcolor={style.shadow_color}"
        f":shadowx={style.shadow_x}"
        f":shadowy={style.shadow_y}"
        f":x={style.position_x}"
        f":y={style.position_y}"
        f":alpha='{alpha}'"
        f":font='{style.font}'"
    )

    return drawtext


def build_watermark_filter(config: WatermarkConfig, video_width: int = 1080) -> tuple[str, str]:
    """Build FFmpeg filter for a watermark/logo overlay.

    Args:
        config: Watermark configuration.
        video_width: Video width for scaling.

    Returns:
        Tuple of (input_args, filter_string) for FFmpeg.
        input_args is the -i flag for the watermark image.
    """
    if not config.image_path or not Path(config.image_path).exists():
        return "", ""

    scale_w = int(video_width * config.scale)

    # Position mapping
    positions = {
        "top-left": (str(config.margin), str(config.margin)),
        "top-right": (f"W-w-{config.margin}", str(config.margin)),
        "bottom-left": (str(config.margin), f"H-h-{config.margin}"),
        "bottom-right": (f"W-w-{config.margin}", f"H-h-{config.margin}"),
    }
    x, y = positions.get(config.position, positions["top-right"])

    # Scale the overlay image, then position it
    filter_str = (
        f"[1:v]scale={scale_w}:-1,format=rgba,"
        f"colorchannelmixer=aa={config.opacity}[wm];"
        f"[0:v][wm]overlay={x}:{y}"
    )

    return f"-i {config.image_path}", filter_str


def apply_hook_overlay(
    video_path: str,
    output_path: str,
    hook_text: str,
    style: HookStyle | None = None,
) -> str:
    """Apply a text hook overlay to a video.

    Args:
        video_path: Input video path.
        output_path: Output video path.
        hook_text: Text to overlay.
        style: Hook styling options.

    Returns:
        Path to the output video.
    """
    if not hook_text:
        logger.info("No hook text provided, skipping overlay")
        # Copy file as-is
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-c", "copy", output_path],
            capture_output=True, check=True,
        )
        return output_path

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    filter_str = build_hook_filter(hook_text, style)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    logger.info("Hook overlay applied: '%s' -> %s", hook_text, output_path)
    return output_path


def apply_watermark(
    video_path: str,
    output_path: str,
    watermark_path: str,
    position: str = "top-right",
    opacity: float = 0.7,
    scale: float = 0.08,
) -> str:
    """Apply a watermark/logo to a video.

    Args:
        video_path: Input video path.
        output_path: Output video path.
        watermark_path: Path to the watermark image (PNG with transparency).
        position: One of top-left, top-right, bottom-left, bottom-right.
        opacity: Watermark opacity (0-1).
        scale: Watermark width as fraction of video width.

    Returns:
        Path to the output video.
    """
    if not watermark_path or not Path(watermark_path).exists():
        logger.warning("Watermark image not found: %s", watermark_path)
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-c", "copy", output_path],
            capture_output=True, check=True,
        )
        return output_path

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    config = WatermarkConfig(
        image_path=watermark_path,
        position=position,
        opacity=opacity,
        scale=scale,
    )

    _, filter_str = build_watermark_filter(config)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", watermark_path,
        "-filter_complex", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    logger.info("Watermark applied: %s -> %s", watermark_path, output_path)
    return output_path
