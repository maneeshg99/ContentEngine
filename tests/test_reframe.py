"""Tests for video reframing logic."""

from content_engine.editor.reframe import compute_crop_positions, smooth_positions


class TestComputeCropPositions:
    def test_basic_center_face(self):
        positions = [{"time": 0.0, "cx": 0.5, "cy": 0.4}]
        crops = compute_crop_positions(positions, src_width=1920, src_height=1080)
        assert len(crops) == 1
        c = crops[0]
        # Crop should be 9:16 aspect from 1080p source
        # crop_h = 1080, crop_w = 1080 * 9/16 = 607
        assert c["h"] == 1080
        assert c["w"] == 607
        # X centered on face at 0.5 -> 960 - 303 = 657
        assert c["x"] >= 0
        assert c["x"] + c["w"] <= 1920

    def test_face_at_left_edge_clamps(self):
        positions = [{"time": 0.0, "cx": 0.0, "cy": 0.5}]
        crops = compute_crop_positions(positions, src_width=1920, src_height=1080)
        assert crops[0]["x"] == 0  # clamped to left edge

    def test_face_at_right_edge_clamps(self):
        positions = [{"time": 0.0, "cx": 1.0, "cy": 0.5}]
        crops = compute_crop_positions(positions, src_width=1920, src_height=1080)
        c = crops[0]
        assert c["x"] + c["w"] <= 1920

    def test_already_portrait_source(self):
        """When source is narrower, crop width equals source width."""
        positions = [{"time": 0.0, "cx": 0.5, "cy": 0.5}]
        crops = compute_crop_positions(positions, src_width=400, src_height=800)
        c = crops[0]
        # 9:16 from 400x800: crop_h = 800, crop_w = 450 > 400
        # So crop_w = 400, crop_h = 400 * 16/9 = 711
        assert c["w"] == 400
        assert c["h"] == 711

    def test_multiple_positions(self):
        positions = [
            {"time": 0.0, "cx": 0.3, "cy": 0.4},
            {"time": 0.5, "cx": 0.5, "cy": 0.4},
            {"time": 1.0, "cx": 0.7, "cy": 0.4},
        ]
        crops = compute_crop_positions(positions, src_width=1920, src_height=1080)
        assert len(crops) == 3
        # All should have same dimensions
        assert all(c["w"] == crops[0]["w"] for c in crops)
        assert all(c["h"] == crops[0]["h"] for c in crops)


class TestSmoothPositions:
    def test_single_position_unchanged(self):
        positions = [{"time": 0.0, "cx": 0.5, "cy": 0.4}]
        result = smooth_positions(positions, total_duration=1.0)
        assert len(result) == 1
        assert result[0]["cx"] == 0.5

    def test_smoothing_averages(self):
        positions = [
            {"time": 0.0, "cx": 0.0, "cy": 0.5},
            {"time": 0.5, "cx": 0.5, "cy": 0.5},
            {"time": 1.0, "cx": 1.0, "cy": 0.5},
        ]
        result = smooth_positions(positions, total_duration=1.0, smoothing_window=3)
        # Middle position should be average of all three: 0.5
        assert result[1]["cx"] == 0.5
        # First position averaged with first two: (0.0 + 0.5) / 2 = 0.25
        assert result[0]["cx"] == 0.25

    def test_empty_returns_empty(self):
        assert smooth_positions([], total_duration=1.0) == []
