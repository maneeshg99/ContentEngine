"""Download video/audio content using yt-dlp."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from content_engine.config import AppConfig
from content_engine.database import Source, SourceStatus, get_session


def _run_ytdlp(url: str, output_dir: str, format_str: str) -> dict:
    """Run yt-dlp and return metadata."""
    output_template = str(Path(output_dir) / "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--format", format_str,
        "--output", output_template,
        "--write-info-json",
        "--no-playlist",
        "--restrict-filenames",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    # Find the info JSON file
    # yt-dlp writes a .info.json file alongside the video
    info_files = list(Path(output_dir).glob("*.info.json"))
    if not info_files:
        raise RuntimeError(f"yt-dlp did not produce info JSON. stderr: {result.stderr}")

    # Get the most recently modified info file
    info_file = max(info_files, key=lambda p: p.stat().st_mtime)
    with open(info_file) as f:
        info = json.load(f)

    # Find the actual media file (same name stem, different extension)
    media_files = [
        p for p in Path(output_dir).iterdir()
        if p.stem == info_file.stem.replace(".info", "") and not p.name.endswith(".json")
    ]
    if not media_files:
        raise RuntimeError(f"Downloaded media file not found in {output_dir}")

    media_path = media_files[0]
    info["_local_path"] = str(media_path)

    return info


def download_source(url: str, config: AppConfig) -> Source:
    """Download a source video/audio and register it in the database."""
    raw_dir = config.storage.raw_dir
    Path(raw_dir).mkdir(parents=True, exist_ok=True)

    info = _run_ytdlp(url, raw_dir, config.downloader.format)

    session = get_session(config)

    source = Source(
        url=url,
        title=info.get("title"),
        channel=info.get("channel") or info.get("uploader"),
        duration=info.get("duration"),
        file_path=info["_local_path"],
        status=SourceStatus.DOWNLOADED,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    return source
