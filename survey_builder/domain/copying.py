"""Duplicating a survey: structure only, never responses."""

import copy

from ..models import BranchRule, Choice, Page, Question, Survey


def copy_survey(survey: Survey, title: str | None = None) -> Survey:
    clone = Survey(
        owner_id=survey.owner_id,
        title=(title or f"Copy of {survey.title}")[:200],
        description=survey.description,
        thank_you_message=survey.thank_you_message,
        allow_multiple=survey.allow_multiple,
        accent_color=survey.accent_color,
    )
    pages: dict[int, Page] = {}
    choices: dict[int, Choice] = {}
    questions: list[tuple[Question, Question]] = []
    for page in survey.pages:
        new_page = Page(title=page.title, description=page.description, position=page.position)
        pages[page.id] = new_page
        for question in page.questions:
            new_question = Question(
                type=question.type,
                prompt=question.prompt,
                help_text=question.help_text,
                required=question.required,
                position=question.position,
                settings=copy.deepcopy(question.settings or {}),
            )
            for choice in question.choices:
                choices[choice.id] = Choice(label=choice.label, position=choice.position)
                new_question.choices.append(choices[choice.id])
            new_page.questions.append(new_question)
            questions.append((question, new_question))
        clone.pages.append(new_page)

    for question, new_question in questions:
        for rule in question.branch_rules:
            new_question.branch_rules.append(
                BranchRule(
                    choice=choices[rule.choice_id],
                    target_page=pages[rule.target_page_id] if rule.target_page_id else None,
                )
            )
    return clone
