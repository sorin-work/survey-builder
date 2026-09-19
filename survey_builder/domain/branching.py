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


def prune_invalid_rules(survey) -> int:
    """Remove rules that no longer point forward (after pages or questions moved).
    Returns how many were removed."""
    removed = 0
    for page in survey.pages:
        allowed = {p.id for p in valid_targets(survey, page)}
        for question in page.questions:
            for rule in list(question.branch_rules):
                if rule.target_page_id is not None and rule.target_page_id not in allowed:
                    question.branch_rules.remove(rule)
                    removed += 1
    return removed


def _always_jumps(page) -> bool:
    """True when every possible answer on the page triggers a skip rule, so the
    page right after it is never shown next."""
    for question in page.questions:
        if question.type != "single_choice" or not question.required or not question.choices:
            continue
        ruled = {rule.choice_id for rule in question.branch_rules}
        if all(choice.id in ruled for choice in question.choices):
            return True
    return False


def unreachable_pages(survey) -> list:
    """Pages that no combination of answers leads to."""
    if not survey.pages:
        return []
    reachable = {survey.pages[0].id}
    for index, page in enumerate(survey.pages):
        if page.id not in reachable:
            continue
        for question in page.questions:
            for rule in question.branch_rules:
                if rule.target_page_id is not None:
                    reachable.add(rule.target_page_id)
        if index + 1 < len(survey.pages) and not _always_jumps(page):
            reachable.add(survey.pages[index + 1].id)
    return [page for page in survey.pages if page.id not in reachable]
