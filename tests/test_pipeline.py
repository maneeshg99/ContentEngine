"""Tests for the automated clip selection pipeline."""

from content_engine.clipper.pipeline import _deduplicate_segments
from content_engine.clipper.scorer import ScoredSegment


def _make_segment(start, end, score):
    return ScoredSegment(
        start=start, end=end, text="test", score=score,
        reasoning="", hook_suggestion="", tags=[],
    )


def test_deduplicate_no_overlap():
    segments = [
        _make_segment(0, 60, 9.0),
        _make_segment(100, 160, 8.0),
        _make_segment(200, 260, 7.0),
    ]
    result = _deduplicate_segments(segments, min_gap=10.0)
    assert len(result) == 3


def test_deduplicate_with_overlap():
    segments = [
        _make_segment(0, 60, 9.0),     # kept (highest score)
        _make_segment(50, 110, 8.0),    # overlaps with first → removed
        _make_segment(200, 260, 7.0),   # no overlap → kept
    ]
    result = _deduplicate_segments(segments, min_gap=10.0)
    assert len(result) == 2
    assert result[0].score == 9.0
    assert result[1].score == 7.0


def test_deduplicate_adjacent_within_gap():
    segments = [
        _make_segment(0, 60, 9.0),
        _make_segment(65, 125, 8.0),  # 5s gap < 10s min_gap → removed
    ]
    result = _deduplicate_segments(segments, min_gap=10.0)
    assert len(result) == 1


def test_deduplicate_adjacent_outside_gap():
    segments = [
        _make_segment(0, 60, 9.0),
        _make_segment(75, 135, 8.0),  # 15s gap > 10s min_gap → kept
    ]
    result = _deduplicate_segments(segments, min_gap=10.0)
    assert len(result) == 2


def test_deduplicate_empty():
    assert _deduplicate_segments([], min_gap=10.0) == []
