"""Tests for caption generation."""

import json
import tempfile
from pathlib import Path

from content_engine.editor.captions import (
    CaptionStyle,
    WordTimestamp,
    _format_ass_time,
    generate_ass_subtitles,
    load_word_timestamps,
    write_ass_file,
)


def _make_transcript(words_data):
    """Create a minimal transcript dict with word timestamps."""
    return {
        "text": " ".join(w["word"] for w in words_data),
        "segments": [
            {
                "id": 0,
                "start": words_data[0]["start"],
                "end": words_data[-1]["end"],
                "text": " ".join(w["word"] for w in words_data),
                "words": words_data,
            }
        ],
    }


class TestFormatAssTime:
    def test_zero(self):
        assert _format_ass_time(0) == "0:00:00.00"

    def test_seconds(self):
        assert _format_ass_time(5.25) == "0:00:05.25"

    def test_minutes(self):
        assert _format_ass_time(65.5) == "0:01:05.50"

    def test_hours(self):
        result = _format_ass_time(3661.0)
        assert result.startswith("1:01:01")


class TestLoadWordTimestamps:
    def test_load_full_range(self, tmp_path):
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
            {"word": "test", "start": 1.0, "end": 1.5},
        ]
        transcript = _make_transcript(words)
        path = tmp_path / "transcript.json"
        path.write_text(json.dumps(transcript))

        result = load_word_timestamps(str(path))
        assert len(result) == 3
        assert result[0].word == "Hello"
        assert result[0].start == 0.0

    def test_load_clipped_range(self, tmp_path):
        words = [
            {"word": "before", "start": 0.0, "end": 5.0},
            {"word": "inside", "start": 10.0, "end": 15.0},
            {"word": "after", "start": 20.0, "end": 25.0},
        ]
        transcript = _make_transcript(words)
        path = tmp_path / "transcript.json"
        path.write_text(json.dumps(transcript))

        result = load_word_timestamps(str(path), clip_start=8.0, clip_end=18.0)
        assert len(result) == 1
        assert result[0].word == "inside"
        # Time should be relative to clip start
        assert result[0].start == 2.0  # 10.0 - 8.0

    def test_empty_transcript(self, tmp_path):
        transcript = {"text": "", "segments": []}
        path = tmp_path / "transcript.json"
        path.write_text(json.dumps(transcript))

        result = load_word_timestamps(str(path))
        assert result == []


class TestGenerateAssSubtitles:
    def test_basic_output(self):
        words = [
            WordTimestamp("Hello", 0.0, 0.5),
            WordTimestamp("world", 0.5, 1.0),
        ]
        result = generate_ass_subtitles(words)
        assert "[Script Info]" in result
        assert "[V4+ Styles]" in result
        assert "[Events]" in result
        assert "Dialogue:" in result

    def test_word_grouping(self):
        words = [WordTimestamp(f"word{i}", i * 0.5, (i + 1) * 0.5) for i in range(8)]
        style = CaptionStyle(words_per_group=4)
        result = generate_ass_subtitles(words, style)
        # Should produce 2 dialogue lines (8 words / 4 per group)
        assert result.count("Dialogue:") == 2

    def test_empty_words(self):
        result = generate_ass_subtitles([])
        assert result == ""

    def test_uppercase_option(self):
        words = [WordTimestamp("hello", 0.0, 0.5)]
        style = CaptionStyle(uppercase=True)
        result = generate_ass_subtitles(words, style)
        assert "HELLO" in result

    def test_karaoke_timing(self):
        words = [WordTimestamp("test", 0.0, 1.0)]
        result = generate_ass_subtitles(words)
        # 1.0 second = 100 centiseconds
        assert "\\kf100" in result


class TestWriteAssFile:
    def test_writes_file(self, tmp_path):
        content = "[Script Info]\nTest content"
        output = str(tmp_path / "test.ass")
        result = write_ass_file(content, output)
        assert Path(result).exists()
        assert Path(result).read_text() == content

    def test_creates_parent_dirs(self, tmp_path):
        output = str(tmp_path / "sub" / "dir" / "test.ass")
        write_ass_file("content", output)
        assert Path(output).exists()
