"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class StorageConfig(BaseModel):
    raw_dir: str = "data/raw"
    clips_dir: str = "data/clips"
    rendered_dir: str = "data/rendered"
    transcripts_dir: str = "data/transcripts"


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///data/content_engine.db"


class WhisperConfig(BaseModel):
    model: str = "base"
    device: str = "cpu"
    language: str | None = None


class DownloaderConfig(BaseModel):
    max_concurrent: int = 3
    format: str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    rate_limit: int | None = None


class ClipperConfig(BaseModel):
    min_duration: int = 30
    max_duration: int = 90
    padding: int = 2


class PlatformConfig(BaseModel):
    enabled: bool = True


class PlatformsConfig(BaseModel):
    youtube: PlatformConfig = PlatformConfig()
    tiktok: PlatformConfig = PlatformConfig()
    instagram: PlatformConfig = PlatformConfig()


class AppConfig(BaseModel):
    storage: StorageConfig = StorageConfig()
    database: DatabaseConfig = DatabaseConfig()
    whisper: WhisperConfig = WhisperConfig()
    downloader: DownloaderConfig = DownloaderConfig()
    clipper: ClipperConfig = ClipperConfig()
    platforms: PlatformsConfig = PlatformsConfig()


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    """Load configuration from YAML file, falling back to defaults."""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)
    return AppConfig()
