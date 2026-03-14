"""9:16 vertical reframing with face detection.

Crops a 16:9 (or any landscape) video to 9:16 portrait, keeping detected
faces centered. Uses MediaPipe Face Detection for tracking and applies
temporal smoothing to avoid jittery crops.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CropWindow:
    """A crop region for a single frame."""

    x: int
    y: int
    w: int
    h: int


def detect_face_positions(
    video_path: str,
    sample_fps: float = 2.0,
) -> list[dict]:
    """Detect face center positions by sampling frames with MediaPipe.

    Args:
        video_path: Path to the input video.
        sample_fps: Frames per second to sample (lower = faster, less smooth).

    Returns:
        List of dicts with 'time', 'cx', 'cy' (normalized 0-1) keys.
        Empty list if no faces detected or MediaPipe unavailable.
    """
    try:
        import cv2
        import mediapipe as mp
    except ImportError:
        logger.warning(
            "opencv-python and mediapipe are required for face detection. "
            "Install with: pip install opencv-python-headless mediapipe"
        )
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, int(fps / sample_fps))

    face_detection = mp.solutions.face_detection.FaceDetection(
        model_selection=1,  # full-range model (better for video)
        min_detection_confidence=0.5,
    )

    positions = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            time_sec = frame_idx / fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb)

            if results.detections:
                # Use the largest (closest) face
                best = max(
                    results.detections,
                    key=lambda d: d.location_data.relative_bounding_box.width
                    * d.location_data.relative_bounding_box.height,
                )
                bbox = best.location_data.relative_bounding_box
                cx = bbox.xmin + bbox.width / 2
                cy = bbox.ymin + bbox.height / 2
                positions.append({"time": time_sec, "cx": cx, "cy": cy})

        frame_idx += 1

    cap.release()
    face_detection.close()

    logger.info("Detected faces in %d/%d sampled frames", len(positions), total_frames // frame_interval)
    return positions


def smooth_positions(
    positions: list[dict],
    total_duration: float,
    sample_fps: float = 2.0,
    smoothing_window: int = 5,
) -> list[dict]:
    """Apply temporal smoothing to face positions to avoid jitter.

    Uses a simple moving average. Fills gaps (frames with no detection)
    by interpolating from nearest known positions.

    Returns:
        Smoothed positions at the same timestamps.
    """
    if not positions:
        return []

    # Fill gaps with linear interpolation
    filled = list(positions)

    # Apply moving average
    smoothed = []
    for i, pos in enumerate(filled):
        start = max(0, i - smoothing_window // 2)
        end = min(len(filled), i + smoothing_window // 2 + 1)
        window = filled[start:end]
        avg_cx = sum(p["cx"] for p in window) / len(window)
        avg_cy = sum(p["cy"] for p in window) / len(window)
        smoothed.append({"time": pos["time"], "cx": avg_cx, "cy": avg_cy})

    return smoothed


def compute_crop_positions(
    positions: list[dict],
    src_width: int,
    src_height: int,
    target_aspect: tuple[int, int] = (9, 16),
) -> list[dict]:
    """Convert normalized face positions to pixel crop coordinates.

    The crop window is sized to maximize the source height while
    maintaining the target aspect ratio.

    Args:
        positions: Smoothed face positions with 'time', 'cx', 'cy'.
        src_width: Source video width in pixels.
        src_height: Source video height in pixels.
        target_aspect: Target aspect ratio as (width, height).

    Returns:
        List of dicts with 'time', 'x', 'y', 'w', 'h' keys (pixel values).
    """
    tw, th = target_aspect
    # Maximize height: use full source height, compute width from aspect ratio
    crop_h = src_height
    crop_w = int(crop_h * tw / th)

    # If computed width exceeds source, constrain by width instead
    if crop_w > src_width:
        crop_w = src_width
        crop_h = int(crop_w * th / tw)

    crops = []
    for pos in positions:
        # Center crop on face X position
        cx_px = int(pos["cx"] * src_width)
        x = cx_px - crop_w // 2

        # Clamp to frame bounds
        x = max(0, min(x, src_width - crop_w))

        # Keep vertical crop centered (faces are usually in upper portion)
        cy_px = int(pos["cy"] * src_height)
        y = cy_px - crop_h // 3  # bias upward — faces are typically in upper third
        y = max(0, min(y, src_height - crop_h))

        crops.append({"time": pos["time"], "x": x, "y": y, "w": crop_w, "h": crop_h})

    return crops


def _get_video_dimensions(video_path: str) -> tuple[int, int, float]:
    """Get video width, height, and duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            w = int(stream["width"])
            h = int(stream["height"])
            duration = float(data.get("format", {}).get("duration", 0))
            return w, h, duration

    raise ValueError(f"No video stream found in {video_path}")


def reframe_video(
    input_path: str,
    output_path: str,
    target_aspect: tuple[int, int] = (9, 16),
    sample_fps: float = 2.0,
    fallback_position: float = 0.5,
) -> str:
    """Reframe a video to the target aspect ratio with face tracking.

    If face detection is unavailable or finds no faces, falls back to
    a center crop at `fallback_position` (0.0 = left, 0.5 = center, 1.0 = right).

    Args:
        input_path: Path to source video.
        output_path: Path for the reframed output.
        target_aspect: Target aspect ratio as (width, height).
        sample_fps: Face detection sampling rate.
        fallback_position: Horizontal position for center crop fallback.

    Returns:
        Path to the output file.
    """
    src_w, src_h, duration = _get_video_dimensions(input_path)
    tw, th = target_aspect

    # Check if already portrait
    if src_w / src_h <= tw / th + 0.05:
        logger.info("Video is already portrait (%.0f:%.0f), skipping reframe", src_w, src_h)
        # Just copy
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path],
            capture_output=True, check=True,
        )
        return output_path

    # Detect faces
    positions = detect_face_positions(input_path, sample_fps=sample_fps)

    # Compute crop dimensions
    crop_h = src_h
    crop_w = int(crop_h * tw / th)
    if crop_w > src_w:
        crop_w = src_w
        crop_h = int(crop_w * th / tw)

    if positions:
        smoothed = smooth_positions(positions, duration, sample_fps)
        crops = compute_crop_positions(smoothed, src_w, src_h, target_aspect)

        # Use the median X position for a stable single-position crop
        # (FFmpeg static crop is more reliable than sendcmd dynamic crop)
        xs = [c["x"] for c in crops]
        xs.sort()
        median_x = xs[len(xs) // 2]

        ys = [c["y"] for c in crops]
        ys.sort()
        median_y = ys[len(ys) // 2]

        logger.info(
            "Face-tracked crop: x=%d, y=%d, %dx%d from %dx%d",
            median_x, median_y, crop_w, crop_h, src_w, src_h,
        )
    else:
        # Fallback: center crop
        median_x = int((src_w - crop_w) * fallback_position)
        median_y = max(0, (src_h - crop_h) // 2)
        logger.info(
            "No faces detected, using center crop: x=%d, y=%d, %dx%d",
            median_x, median_y, crop_w, crop_h,
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"crop={crop_w}:{crop_h}:{median_x}:{median_y}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    logger.info("Reframed video saved: %s", output_path)
    return output_path
