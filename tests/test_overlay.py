"""Tests for overlay module."""

from content_engine.editor.overlay import HookStyle, WatermarkConfig, build_hook_filter, build_watermark_filter


class TestBuildHookFilter:
    def test_basic_filter(self):
        result = build_hook_filter("Wait for it...")
        assert "drawtext=" in result
        assert "Wait for it" in result
        assert "alpha=" in result

    def test_custom_style(self):
        style = HookStyle(font_size=72, duration=3.0, font_color="yellow")
        result = build_hook_filter("Test", style)
        assert "fontsize=72" in result
        assert "fontcolor=yellow" in result

    def test_special_characters_escaped(self):
        result = build_hook_filter("100% real: facts")
        # Colon should be escaped for FFmpeg
        assert "\\:" in result
        # Percent should be doubled
        assert "%%" in result

    def test_empty_text(self):
        result = build_hook_filter("")
        assert "drawtext=" in result


class TestBuildWatermarkFilter:
    def test_no_image_returns_empty(self):
        config = WatermarkConfig(image_path="")
        input_args, filter_str = build_watermark_filter(config)
        assert input_args == ""
        assert filter_str == ""

    def test_nonexistent_image_returns_empty(self):
        config = WatermarkConfig(image_path="/nonexistent/logo.png")
        input_args, filter_str = build_watermark_filter(config)
        assert input_args == ""
        assert filter_str == ""

    def test_valid_config_builds_filter(self, tmp_path):
        logo = tmp_path / "logo.png"
        logo.write_bytes(b"fake png")
        config = WatermarkConfig(
            image_path=str(logo),
            position="bottom-right",
            opacity=0.5,
            scale=0.1,
        )
        input_args, filter_str = build_watermark_filter(config, video_width=1080)
        assert str(logo) in input_args
        assert "overlay=" in filter_str
        assert "0.5" in filter_str  # opacity
