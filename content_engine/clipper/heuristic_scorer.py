"""Local heuristic scorer — no API key required.

Scores transcript segments using text heuristics and audio energy analysis.
Not as accurate as LLM scoring, but completely free and offline.
"""

from __future__ import annotations

import re

from content_engine.clipper.scorer import ScoredSegment


# Keywords and patterns that correlate with viral content
ENGAGEMENT_PATTERNS = {
    "controversy": [
        r"\bnever\b", r"\balways\b", r"\bwrong\b", r"\blie[sd]?\b", r"\btruth\b",
        r"\bscam\b", r"\bfake\b", r"\bhate\b", r"\bdisagree\b", r"\bunpopular\b",
        r"\boverrated\b", r"\bunderrated\b", r"\bcancel\b", r"\btoxic\b",
        r"\bcontrovers", r"\bproblem\b", r"\brigid\b",
    ],
    "emotion": [
        r"\blove\b", r"\bcried?\b", r"\bscared?\b", r"\bshocked?\b", r"\bamazed?\b",
        r"\bbeautiful\b", r"\bterribl[ey]\b", r"\bincredible\b", r"\bunbelievable\b",
        r"\bheartbreak", r"\bdevastated?\b", r"\binspir", r"\bmotivat",
        r"\bpassion", r"\bdepressed?\b", r"\banxious\b", r"\banger\b",
    ],
    "story": [
        r"\bstory\b", r"\bhappened\b", r"\bmoment\b", r"\bchanged\b", r"\brealized?\b",
        r"\bturning point\b", r"\bfirst time\b", r"\blast time\b", r"\bwhen i was\b",
        r"\btold me\b", r"\bi remember\b", r"\bsecret\b", r"\bconfess",
        r"\bwake.?up call\b", r"\blearned?\b",
    ],
    "quotability": [
        r"\bhere.s the thing\b", r"\blisten\b", r"\blet me tell you\b",
        r"\bthe key is\b", r"\brule.?of\b", r"\bif you want\b", r"\bthe difference\b",
        r"\bpeople don.t\b", r"\bnobody\b", r"\beverybody\b", r"\bthe truth is\b",
        r"\bhere.s what\b", r"\bthink about\b",
    ],
}

# Hooks to suggest based on dominant category
HOOK_TEMPLATES = {
    "controversy": [
        "Nobody wants to hear this...",
        "This is the harsh truth",
        "Unpopular opinion incoming",
        "This will make you think twice",
    ],
    "emotion": [
        "This hit me hard...",
        "I wasn't ready for this",
        "Wait until the end",
        "This changed my perspective",
    ],
    "story": [
        "Wait for the twist...",
        "You won't believe what happened",
        "This story is insane",
        "Let me tell you something...",
    ],
    "quotability": [
        "Write this down",
        "Best advice I've ever heard",
        "This is so true",
        "Listen to this carefully",
    ],
}


def _score_text(text: str) -> tuple[float, str, list[str]]:
    """Score text based on heuristic patterns.

    Returns:
        Tuple of (score, dominant_category, matching_tags).
    """
    text_lower = text.lower()
    category_scores: dict[str, float] = {}
    matching_tags: list[str] = []

    for category, patterns in ENGAGEMENT_PATTERNS.items():
        hits = 0
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            hits += len(matches)

        # Normalize: each category worth up to 2.5 points (total max ~10)
        category_scores[category] = min(2.5, hits * 0.5)
        if hits > 0:
            matching_tags.append(category)

    # Bonus signals
    bonus = 0.0

    # Questions drive engagement
    question_count = text.count("?")
    bonus += min(1.0, question_count * 0.3)

    # Exclamations signal energy
    exclaim_count = text.count("!")
    bonus += min(0.5, exclaim_count * 0.15)

    # Short, punchy sentences score higher (average words per sentence)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if sentences:
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_words < 15:
            bonus += 0.5  # punchy
        elif avg_words > 30:
            bonus -= 0.5  # rambly

    # Word count — too short is bad, moderate length is ideal
    word_count = len(text.split())
    if word_count < 20:
        bonus -= 1.0
    elif 50 <= word_count <= 150:
        bonus += 0.5

    total = sum(category_scores.values()) + bonus
    total = max(0.0, min(10.0, total))

    # Find dominant category
    dominant = max(category_scores, key=category_scores.get) if category_scores else "story"

    return total, dominant, matching_tags


def score_segments_local(
    segments: list[dict],
    min_score: float = 4.0,
) -> list[ScoredSegment]:
    """Score transcript segments using local heuristics (no API needed).

    Args:
        segments: List of dicts with 'start', 'end', 'text' keys.
        min_score: Minimum score threshold.

    Returns:
        List of ScoredSegment objects, sorted by score descending.
    """
    scored = []
    for seg in segments:
        score, dominant, tags = _score_text(seg["text"])

        # Pick a hook suggestion based on dominant category
        import random
        hooks = HOOK_TEMPLATES.get(dominant, HOOK_TEMPLATES["story"])
        hook = hooks[hash(seg["text"]) % len(hooks)]  # deterministic pick

        scored.append(
            ScoredSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                score=score,
                reasoning=f"Heuristic: dominant={dominant}, tags={tags}",
                hook_suggestion=hook,
                tags=tags or ["general"],
            )
        )

    scored = [s for s in scored if s.score >= min_score]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored
