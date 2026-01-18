"""Duplicating a survey: structure only, never responses."""

import copy

from ..models import Choice, Page, Question, Survey


def copy_survey(survey: Survey, title: str | None = None) -> Survey:
    clone = Survey(
        owner_id=survey.owner_id,
        title=(title or f"Copy of {survey.title}")[:200],
        description=survey.description,
        thank_you_message=survey.thank_you_message,
    )
    for page in survey.pages:
        new_page = Page(title=page.title, position=page.position)
        for question in page.questions:
            new_question = Question(
                type=question.type,
                prompt=question.prompt,
                help_text=question.help_text,
                required=question.required,
                position=question.position,
                settings=copy.deepcopy(question.settings or {}),
            )
            new_question.choices = [
                Choice(label=c.label, position=c.position) for c in question.choices
            ]
            new_page.questions.append(new_question)
        clone.pages.append(new_page)
    return clone
