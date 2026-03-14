"""Tests for configuration loading."""

from content_engine.config import AppConfig, load_config


def test_default_config():
    """Default config should load without a file."""
    config = load_config("nonexistent.yaml")
    assert isinstance(config, AppConfig)
    assert config.whisper.model == "base"
    assert config.clipper.min_duration == 30
    assert config.clipper.max_duration == 90


def test_storage_defaults():
    config = AppConfig()
    assert config.storage.raw_dir == "data/raw"
    assert config.storage.clips_dir == "data/clips"


def test_platform_defaults():
    config = AppConfig()
    assert config.platforms.youtube.enabled is True
    assert config.platforms.tiktok.enabled is True
    assert config.platforms.instagram.enabled is True
