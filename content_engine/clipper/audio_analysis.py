"""Audio energy analysis for detecting engaging segments."""

from __future__ import annotations

import subprocess
import struct
import wave
from pathlib import Path


def get_energy_peaks(
    file_path: str,
    window_seconds: float = 5.0,
    top_n: int = 10,
) -> list[dict]:
    """Analyze audio energy and return timestamps of peak moments.

    Converts input to WAV, computes RMS energy in sliding windows,
    and returns the top N peak windows sorted by energy.

    Args:
        file_path: Path to audio/video file.
        window_seconds: Size of the analysis window in seconds.
        top_n: Number of top peaks to return.

    Returns:
        List of dicts with 'start', 'end', 'energy' keys, sorted by energy descending.
    """
    # Convert to temporary WAV for analysis
    tmp_wav = Path(file_path).with_suffix(".analysis.wav")

    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", file_path,
            "-ac", "1",          # mono
            "-ar", "16000",      # 16kHz sample rate
            "-f", "wav",
            str(tmp_wav),
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        with wave.open(str(tmp_wav), "rb") as wf:
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_data = wf.readframes(n_frames)

        # Parse 16-bit signed samples
        samples = struct.unpack(f"<{n_frames}h", raw_data)
        window_size = int(window_seconds * sample_rate)

        # Compute RMS energy for each window
        windows = []
        for i in range(0, len(samples) - window_size, window_size // 2):  # 50% overlap
            chunk = samples[i : i + window_size]
            rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
            start_sec = i / sample_rate
            end_sec = (i + window_size) / sample_rate
            windows.append({"start": start_sec, "end": end_sec, "energy": rms})

        # Sort by energy and return top N
        windows.sort(key=lambda w: w["energy"], reverse=True)
        return windows[:top_n]

    finally:
        if tmp_wav.exists():
            tmp_wav.unlink()
