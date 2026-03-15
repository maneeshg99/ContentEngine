"""Tests for the local heuristic scorer."""

from content_engine.clipper.heuristic_scorer import _score_text, score_segments_local


class TestScoreText:
    def test_controversial_text_scores_higher(self):
        bland = "The weather is nice today and we went for a walk."
        spicy = "That's a complete lie and everybody knows it. The truth is they're wrong about everything."
        bland_score, _, _ = _score_text(bland)
        spicy_score, _, _ = _score_text(spicy)
        assert spicy_score > bland_score

    def test_emotional_text_detected(self):
        text = "I cried when I heard that. It was absolutely incredible and heartbreaking."
        score, dominant, tags = _score_text(text)
        assert score > 0
        assert "emotion" in tags

    def test_story_patterns_detected(self):
        text = "Let me tell you what happened. The moment I realized the truth, everything changed."
        score, dominant, tags = _score_text(text)
        assert "story" in tags

    def test_questions_boost_score(self):
        no_q = "This is a statement about something interesting."
        with_q = "This is a statement about something interesting? Really? Are you sure?"
        score_no, _, _ = _score_text(no_q)
        score_q, _, _ = _score_text(with_q)
        assert score_q > score_no

    def test_very_short_text_penalized(self):
        short = "Hello world."
        score, _, _ = _score_text(short)
        assert score < 3.0

    def test_score_bounded_0_to_10(self):
        # Even extreme text should stay in bounds
        extreme = "lie wrong hate scam fake truth " * 20
        score, _, _ = _score_text(extreme)
        assert 0.0 <= score <= 10.0

    def test_empty_text(self):
        score, _, _ = _score_text("")
        assert score >= 0.0


class TestScoreSegmentsLocal:
    def test_returns_sorted_by_score(self):
        segments = [
            {"start": 0, "end": 60, "text": "The weather is nice today and everything is fine and normal."},
            {"start": 60, "end": 120, "text": "That's a complete lie! Nobody believes this scam. The truth will come out and everybody knows it."},
        ]
        results = score_segments_local(segments, min_score=0.0)
        assert len(results) == 2
        assert results[0].score >= results[1].score

    def test_min_score_filters(self):
        segments = [
            {"start": 0, "end": 60, "text": "Hello."},
        ]
        results = score_segments_local(segments, min_score=9.0)
        assert len(results) == 0

    def test_hook_suggestion_provided(self):
        segments = [
            {"start": 0, "end": 60, "text": "I cried when I heard the incredible story. It was unbelievable and devastating."},
        ]
        results = score_segments_local(segments, min_score=0.0)
        assert len(results) == 1
        assert results[0].hook_suggestion != ""

    def test_tags_populated(self):
        segments = [
            {"start": 0, "end": 60, "text": "The truth is this was a lie and everyone was wrong about it."},
        ]
        results = score_segments_local(segments, min_score=0.0)
        assert len(results[0].tags) > 0
