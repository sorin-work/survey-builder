"""Order in which a respondent sees the options of each question."""

import random


def choice_order(page, seed: str) -> dict[int, list]:
    """Per-question choice lists, shuffled where the question asks for it.

    The order is stable for one respondent (same seed) so options do not jump
    around when a page is shown again with validation errors or after Back.
    """
    orders = {}
    for question in page.questions:
        choices = list(question.choices)
        if (question.settings or {}).get("shuffle"):
            random.Random(f"{seed}:{question.id}").shuffle(choices)
        orders[question.id] = choices
    return orders
