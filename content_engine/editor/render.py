"""Final render pipeline — chains reframing, captions, and overlays.

Orchestrates the full post-production flow for a clip:
1. Reframe to 9:16 (with face tracking)
2. Generate and burn captions
3. Apply text hook overlay
4. Apply watermark (optional)
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from content_engine.config import AppConfig
from content_engine.database import Clip, ClipStatus
from content_engine.editor.captions import CaptionStyle, burn_captions, generate_captions_for_clip
from content_engine.editor.overlay import HookStyle, apply_hook_overlay, apply_watermark
from content_engine.editor.reframe import reframe_video

logger = logging.getLogger(__name__)


@dataclass
class RenderOptions:
    """Options controlling which post-production steps to apply."""

    reframe: bool = True
    target_aspect: tuple[int, int] = (9, 16)
    captions: bool = True
    caption_style: CaptionStyle = field(default_factory=CaptionStyle)
    hook_text: str = ""
    hook_style: HookStyle = field(default_factory=HookStyle)
    watermark_path: str = ""
    watermark_position: str = "top-right"
    watermark_opacity: float = 0.7


def render_clip(
    clip: Clip,
    config: AppConfig,
    session,
    transcript_path: str | None = None,
    options: RenderOptions | None = None,
) -> str:
    """Run the full post-production pipeline on a clip.

    Args:
        clip: The Clip database record (must have file_path set).
        config: Application configuration.
        session: Database session.
        transcript_path: Path to the source transcript JSON (needed for captions).
        options: Render options controlling which steps to apply.

    Returns:
        Path to the final rendered video.
    """
    if options is None:
        options = RenderOptions()

    if not clip.file_path or not Path(clip.file_path).exists():
        raise FileNotFoundError(f"Clip file not found: {clip.file_path}")

    rendered_dir = Path(config.storage.rendered_dir)
    rendered_dir.mkdir(parents=True, exist_ok=True)
    final_output = str(rendered_dir / f"clip_{clip.id}_rendered.mp4")

    # Use a temp directory for intermediate files
    with tempfile.TemporaryDirectory(prefix="ce_render_") as tmpdir:
        current_path = clip.file_path
        step = 0

        # Step 1: Reframe to 9:16
        if options.reframe:
            step += 1
            reframed_path = str(Path(tmpdir) / f"step{step}_reframed.mp4")
            logger.info("Step %d: Reframing to %d:%d", step, *options.target_aspect)
            current_path = reframe_video(
                current_path,
                reframed_path,
                target_aspect=options.target_aspect,
            )

        # Step 2: Captions
        if options.captions and transcript_path and Path(transcript_path).exists():
            step += 1
            ass_path = str(Path(tmpdir) / f"step{step}_captions.ass")
            captioned_path = str(Path(tmpdir) / f"step{step}_captioned.mp4")

            logger.info("Step %d: Generating captions", step)
            ass_file = generate_captions_for_clip(
                transcript_path,
                clip_start=clip.start_time,
                clip_end=clip.end_time,
                output_ass_path=ass_path,
                style=options.caption_style,
            )

            if ass_file:
                current_path = burn_captions(current_path, ass_file, captioned_path)
            else:
                logger.warning("No captions generated (no word timestamps?)")

        # Step 3: Text hook overlay
        if options.hook_text:
            step += 1
            hook_path = str(Path(tmpdir) / f"step{step}_hook.mp4")
            logger.info("Step %d: Adding hook overlay: '%s'", step, options.hook_text)
            current_path = apply_hook_overlay(
                current_path,
                hook_path,
                options.hook_text,
                style=options.hook_style,
            )

        # Step 4: Watermark
        if options.watermark_path:
            step += 1
            wm_path = str(Path(tmpdir) / f"step{step}_watermark.mp4")
            logger.info("Step %d: Adding watermark", step)
            current_path = apply_watermark(
                current_path,
                wm_path,
                options.watermark_path,
                position=options.watermark_position,
                opacity=options.watermark_opacity,
            )

        # Copy final result to rendered directory
        shutil.copy2(current_path, final_output)

    # Update database
    clip.status = ClipStatus.RENDERED
    session.commit()

    logger.info("Render complete: %s (%d steps)", final_output, step)
    return final_output


def render_clip_simple(
    clip: Clip,
    config: AppConfig,
    session,
    transcript_path: str | None = None,
    hook_text: str = "",
    reframe: bool = True,
    captions: bool = True,
    watermark_path: str = "",
) -> str:
    """Simplified render interface with common defaults.

    A convenience wrapper around render_clip for CLI usage.
    """
    options = RenderOptions(
        reframe=reframe,
        captions=captions,
        hook_text=hook_text,
        watermark_path=watermark_path,
    )
    return render_clip(clip, config, session, transcript_path, options)
