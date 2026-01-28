"""Skip logic: which page comes after the one a respondent just submitted."""


def next_page(survey, page, answers):
    """The page to show after ``page`` given the answers submitted on it,
    or None when the survey is finished.

    Rules are checked question by question in page order; the first rule whose
    choice was picked wins. Without a matching rule the next page in order follows.
    """
    picked = {answer.question_id: set(answer.choice_ids) for answer in answers}
    for question in page.questions:
        chosen = picked.get(question.id)
        if not chosen:
            continue
        for rule in question.branch_rules:
            if rule.choice_id in chosen:
                return rule.target_page
    index = survey.pages.index(page)
    return survey.pages[index + 1] if index + 1 < len(survey.pages) else None


def valid_targets(survey, page):
    """Pages a rule on ``page`` may jump to: only later pages, so there are no loops."""
    index = survey.pages.index(page)
    return survey.pages[index + 1 :]
