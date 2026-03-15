"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator


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

    @field_validator("device")
    @classmethod
    def validate_device(cls, v: str) -> str:
        v = v.lower().strip()
        if v == "rocm":
            raise ValueError(
                "Use device='cuda' for AMD ROCm GPUs (ROCm uses PyTorch's CUDA interface). "
                "See docs/gpu-setup.md"
            )
        if v not in ("cpu", "cuda", "directml"):
            raise ValueError(f"device must be 'cpu', 'cuda', or 'directml', got '{v}'")
        return v


class DownloaderConfig(BaseModel):
    max_concurrent: int = 3
    format: str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    rate_limit: int | None = None


class ClipperConfig(BaseModel):
    min_duration: int = 30
    max_duration: int = 90
    padding: int = 2


class EditorConfig(BaseModel):
    reframe: bool = True
    captions: bool = True
    caption_font: str = "Arial"
    caption_font_size: int = 20
    caption_color: str = "&H00FFFFFF"
    caption_highlight_color: str = "&H0000FFFF"
    caption_words_per_group: int = 4
    caption_uppercase: bool = True
    watermark_path: str = ""
    watermark_position: str = "top-right"
    watermark_opacity: float = 0.7


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
    editor: EditorConfig = EditorConfig()
    platforms: PlatformsConfig = PlatformsConfig()


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    """Load configuration from YAML file, falling back to defaults."""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)
    return AppConfig()
