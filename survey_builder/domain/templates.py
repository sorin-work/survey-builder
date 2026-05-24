"""Ready-made surveys to start from."""

from dataclasses import dataclass, field

from ..models import Choice, Page, Question, Survey


@dataclass(frozen=True)
class TemplateQuestion:
    type: str
    prompt: str
    required: bool = False
    choices: tuple[str, ...] = ()
    settings: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SurveyTemplate:
    key: str
    title: str
    description: str
    pages: tuple[tuple[TemplateQuestion, ...], ...]

    @property
    def question_count(self) -> int:
        return sum(len(page) for page in self.pages)


Q = TemplateQuestion

TEMPLATES: dict[str, SurveyTemplate] = {
    t.key: t
    for t in [
        SurveyTemplate(
            "nps",
            "Net Promoter Score",
            "The classic loyalty question plus a follow-up asking why.",
            (
                (
                    Q(
                        "nps",
                        "How likely are you to recommend us to a friend or colleague?",
                        required=True,
                        settings={
                            "low_label": "Not at all likely",
                            "high_label": "Extremely likely",
                        },
                    ),
                    Q("long_text", "What is the main reason for your score?"),
                ),
            ),
        ),
        SurveyTemplate(
            "event",
            "Event feedback",
            "Find out how your event went and what to change next time.",
            (
                (
                    Q(
                        "rating",
                        "Overall, how would you rate the event?",
                        True,
                        settings={"scale": 5},
                    ),
                    Q(
                        "multiple_choice",
                        "Which parts did you enjoy?",
                        choices=("Talks", "Workshops", "Networking", "Food", "Venue"),
                    ),
                ),
                (
                    Q(
                        "single_choice",
                        "Would you come again?",
                        True,
                        choices=("Definitely", "Maybe", "No"),
                    ),
                    Q("long_text", "What should we do differently?"),
                ),
            ),
        ),
        SurveyTemplate(
            "pulse",
            "Employee pulse",
            "A short, regular check-in on how the team is doing.",
            (
                (
                    Q(
                        "rating",
                        "How do you feel about your work this week?",
                        True,
                        settings={"scale": 5},
                    ),
                    Q("rating", "How manageable is your workload?", True, settings={"scale": 5}),
                    Q(
                        "single_choice",
                        "Do you have what you need to do your job well?",
                        choices=("Yes", "Mostly", "No"),
                    ),
                    Q("long_text", "Anything you would like to share anonymously?"),
                ),
            ),
        ),
    ]
}


def build_from_template(template: SurveyTemplate, owner_id: int) -> Survey:
    survey = Survey(owner_id=owner_id, title=template.title, description=template.description)
    for page_index, questions in enumerate(template.pages):
        page = Page(position=page_index)
        for position, spec in enumerate(questions):
            question = Question(
                type=spec.type,
                prompt=spec.prompt,
                required=spec.required,
                position=position,
                settings=dict(spec.settings),
            )
            question.choices = [
                Choice(label=label, position=i) for i, label in enumerate(spec.choices)
            ]
            page.questions.append(question)
        survey.pages.append(page)
    return survey
