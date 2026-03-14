"""Transcription using OpenAI Whisper."""

from __future__ import annotations

import json
from pathlib import Path

import whisper

from content_engine.config import AppConfig
from content_engine.database import Source, SourceStatus


def transcribe_source(source: Source, config: AppConfig, session) -> str:
    """Transcribe a source file using Whisper.

    Returns the path to the transcript JSON file.
    """
    transcripts_dir = Path(config.storage.transcripts_dir)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    model = whisper.load_model(config.whisper.model, device=config.whisper.device)

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
