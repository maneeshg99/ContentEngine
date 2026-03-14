"""Transcription using OpenAI Whisper."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import torch
import whisper

from content_engine.config import AppConfig
from content_engine.database import Source, SourceStatus

logger = logging.getLogger(__name__)


def _resolve_device(requested: str) -> str:
    """Resolve the compute device, falling back to CPU if GPU is unavailable."""
    if requested == "cpu":
        return "cpu"
    if requested == "directml":
        try:
            import torch_directml  # noqa: F401

            logger.info("Using DirectML (AMD GPU via DirectX 12)")
            return "directml"
        except ImportError:
            logger.warning(
                "DirectML requested but torch-directml is not installed. "
                "Install with: pip install torch-directml. Falling back to CPU."
            )
            return "cpu"
    if requested == "cuda":
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            logger.info("Using GPU: %s", device_name)
            return "cuda"
        logger.warning(
            "GPU requested (device='cuda') but torch.cuda.is_available() is False. "
            "Falling back to CPU. See docs/gpu-setup.md for setup instructions."
        )
        return "cpu"
    return requested


def transcribe_source(source: Source, config: AppConfig, session) -> str:
    """Transcribe a source file using Whisper.

    Returns the path to the transcript JSON file.
    """
    transcripts_dir = Path(config.storage.transcripts_dir)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    device = _resolve_device(config.whisper.device)
    try:
        if device == "directml":
            import torch_directml

            model = whisper.load_model(config.whisper.model, device="cpu")
            model = model.to(torch_directml.device())
        else:
            model = whisper.load_model(config.whisper.model, device=device)
    except RuntimeError as e:
        if device != "cpu":
            logger.warning("GPU model load failed (%s), retrying on CPU.", e)
            model = whisper.load_model(config.whisper.model, device="cpu")
        else:
            raise

    result = model.transcribe(
        source.file_path,
        language=config.whisper.language,
        word_timestamps=True,
        verbose=False,
    )

    # Save full transcript with word-level timestamps
    transcript_data = {
        "source_id": source.id,
        "text": result["text"],
        "language": result.get("language"),
        "segments": [
            {
                "id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
                "words": [
                    {
                        "word": w["word"].strip(),
                        "start": w["start"],
                        "end": w["end"],
                        "probability": w.get("probability", 0),
                    }
                    for w in seg.get("words", [])
                ],
            }
            for seg in result["segments"]
        ],
    }

    # Use source ID as filename
    transcript_path = transcripts_dir / f"source_{source.id}.json"
    with open(transcript_path, "w") as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)

    # Update source record
    source.transcript_path = str(transcript_path)
    source.status = SourceStatus.TRANSCRIBED
    session.commit()

    return str(transcript_path)
