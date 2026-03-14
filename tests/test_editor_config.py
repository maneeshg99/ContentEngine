"""Tests for editor configuration."""

from content_engine.config import AppConfig, EditorConfig


class TestEditorConfig:
    def test_defaults(self):
        config = EditorConfig()
        assert config.reframe is True
        assert config.captions is True
        assert config.caption_font == "Arial"
        assert config.caption_words_per_group == 4
        assert config.watermark_path == ""

    def test_app_config_includes_editor(self):
        config = AppConfig()
        assert hasattr(config, "editor")
        assert isinstance(config.editor, EditorConfig)

    def test_custom_values(self):
        config = EditorConfig(
            reframe=False,
            caption_font_size=32,
            watermark_path="/path/to/logo.png",
        )
        assert config.reframe is False
        assert config.caption_font_size == 32
        assert config.watermark_path == "/path/to/logo.png"
