"""Tests for the virality scorer and transcript segmentation."""

from content_engine.clipper.scorer import (
    ScoredSegment,
    _build_segments_text,
    _extract_json_array,
    segment_transcript,
)


def test_build_segments_text():
    segments = [
        {"start": 0.0, "end": 60.0, "text": "First segment text"},
        {"start": 45.0, "end": 120.0, "text": "Second segment text"},
    ]
    result = _build_segments_text(segments)
    assert "Segment 1" in result
    assert "Segment 2" in result
    assert "0.0s - 60.0s" in result
    assert "First segment text" in result


def test_extract_json_array_direct():
    text = '[{"score": 8, "reasoning": "test"}]'
    result = _extract_json_array(text)
    assert len(result) == 1
    assert result[0]["score"] == 8


def test_extract_json_array_from_markdown():
    text = """Here are the results:
```json
[{"score": 7, "reasoning": "good stuff"}]
```"""
    result = _extract_json_array(text)
    assert len(result) == 1
    assert result[0]["score"] == 7


def test_extract_json_array_embedded():
    text = "The analysis shows [{'score': 9}] is the result"
    # This won't parse due to single quotes, but let's test with valid JSON
    text = 'The analysis shows [{"score": 9}] is the result'
    result = _extract_json_array(text)
    assert result[0]["score"] == 9


def test_segment_transcript_basic():
    transcript = {
        "segments": [
            {"id": 0, "start": 0.0, "end": 30.0, "text": " ".join(["word"] * 40)},
            {"id": 1, "start": 30.0, "end": 60.0, "text": " ".join(["more"] * 40)},
            {"id": 2, "start": 60.0, "end": 90.0, "text": " ".join(["stuff"] * 40)},
        ]
    }
    windows = segment_transcript(transcript, window_seconds=60.0, overlap_seconds=15.0)
    assert len(windows) > 0
    assert all("start" in w and "end" in w and "text" in w for w in windows)


def test_segment_transcript_empty():
    assert segment_transcript({"segments": []}) == []
    assert segment_transcript({}) == []


def test_segment_transcript_min_words():
    transcript = {
        "segments": [
            {"id": 0, "start": 0.0, "end": 60.0, "text": "too short"},
        ]
    }
    # Default min_words=30, "too short" only has 2 words
    windows = segment_transcript(transcript, window_seconds=60.0)
    assert len(windows) == 0


def test_segment_transcript_respects_window_size():
    # 5 segments of 30s each = 150s total
    transcript = {
        "segments": [
            {"id": i, "start": i * 30.0, "end": (i + 1) * 30.0, "text": " ".join(["word"] * 40)}
            for i in range(5)
        ]
    }
    windows = segment_transcript(transcript, window_seconds=90.0, overlap_seconds=30.0)
    # Each window should be at most 90s
    for w in windows:
        assert w["end"] - w["start"] <= 90.0
