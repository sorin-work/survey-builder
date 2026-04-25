"""Rough estimate of how long a survey takes to fill in."""

import math

# Seconds a typical respondent spends per question type.
SECONDS_PER_QUESTION = {
    "short_text": 20,
    "long_text": 60,
    "single_choice": 8,
    "multiple_choice": 12,
    "rating": 6,
    "nps": 6,
    "date": 10,
}


def estimated_minutes(questions) -> int:
    seconds = sum(SECONDS_PER_QUESTION.get(q.type, 10) for q in questions)
    if not seconds:
        return 0
    return max(1, math.ceil(seconds / 60))
