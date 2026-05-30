"""Validating the editor's question form."""

from dataclasses import dataclass, field

from .settings import parse_settings

PROMPT_MAX = 500
HELP_MAX = 500
CHOICE_MAX = 300


@dataclass
class QuestionChanges:
    prompt: str
    help_text: str
    required: bool
    settings: dict
    labels: dict = field(default_factory=dict)  # choice id -> new label

    def apply(self, question) -> None:
        question.prompt = self.prompt
        question.help_text = self.help_text
        question.required = self.required
        question.settings = self.settings
        for choice in question.choices:
            if choice.id in self.labels:
                choice.label = self.labels[choice.id]


def parse_question_form(question, form) -> tuple[QuestionChanges, dict[str, str]]:
    prompt = form.get("prompt", "").strip()
    help_text = form.get("help_text", "").strip()
    errors: dict[str, str] = {}
    if not prompt:
        errors["prompt"] = "The question needs some text."
    elif len(prompt) > PROMPT_MAX:
        errors["prompt"] = f"Keep the question under {PROMPT_MAX} characters."
    if len(help_text) > HELP_MAX:
        errors["help_text"] = f"Keep the help text under {HELP_MAX} characters."
    settings, setting_errors = parse_settings(question.type, form)
    errors.update(setting_errors)

    labels = {}
    for choice in question.choices:
        label = form.get(f"choice_{choice.id}")
        if label is None:
            continue
        label = label.strip()
        if not label:
            errors["choices"] = "Options cannot be empty."
        elif len(label) > CHOICE_MAX:
            errors["choices"] = f"Keep options under {CHOICE_MAX} characters."
        labels[choice.id] = label
    if "choices" not in errors and len(set(labels.values())) < len(labels):
        errors["choices"] = "Each option must be different."

    changes = QuestionChanges(
        prompt=prompt,
        help_text=help_text,
        required=form.get("required") == "on",
        settings=settings,
        labels=labels,
    )
    return changes, errors
