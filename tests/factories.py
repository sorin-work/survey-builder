from survey_builder.extensions import db
from survey_builder.models import Page, Survey, User

PASSWORD = "s3cret-pass"


def make_user(email="owner@example.com", name="Owner") -> User:
    user = User(email=email, name=name)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def make_survey(owner: User, title="Customer feedback", **kwargs) -> Survey:
    survey = Survey(owner=owner, title=title, **kwargs)
    survey.pages.append(Page(position=0))
    db.session.add(survey)
    db.session.commit()
    return survey


def login(client, user: User) -> None:
    resp = client.post("/login", data={"email": user.email, "password": PASSWORD})
    assert resp.status_code == 302


def make_published_survey(owner: User, questions_by_page=None, title="Customer feedback"):
    """Build a published survey. ``questions_by_page`` is a list of pages, each a
    list of (type, prompt, kwargs) tuples; choice questions take ``choices``."""
    from survey_builder.models import Choice, Question

    questions_by_page = questions_by_page or [[("short_text", "Your name", {})]]
    survey = Survey(owner=owner, title=title, status="published", share_token=f"tok-{title}")
    for page_index, questions in enumerate(questions_by_page):
        page = Page(position=page_index, title=f"Page {page_index + 1}")
        for position, (qtype, prompt, kwargs) in enumerate(questions):
            kwargs = dict(kwargs)
            labels = kwargs.pop("choices", [])
            question = Question(type=qtype, prompt=prompt, position=position, **kwargs)
            question.choices = [Choice(label=label, position=i) for i, label in enumerate(labels)]
            page.questions.append(question)
        survey.pages.append(page)
    db.session.add(survey)
    db.session.commit()
    return survey


def add_response(survey: Survey, answers: dict, completed=True, when=None):
    """Store a response. ``answers`` maps a Question to a value: a str for text,
    an int for rating/NPS, a date, or a choice label / list of labels."""
    import secrets
    from datetime import date

    from survey_builder.models import Answer, Response, utcnow

    response = Response(survey=survey, key=secrets.token_hex(8))
    db.session.add(response)
    if completed:
        response.completed_at = when or utcnow()
    for question, value in answers.items():
        if question.type in ("single_choice", "multiple_choice"):
            labels = value if isinstance(value, list) else [value]
            by_label = {c.label: c for c in question.choices}
            for label in labels:
                response.answers.append(Answer(question=question, choice=by_label[label]))
        elif isinstance(value, date):
            response.answers.append(Answer(question=question, date_value=value))
        elif isinstance(value, int):
            response.answers.append(Answer(question=question, number_value=value))
        else:
            response.answers.append(Answer(question=question, text_value=value))
    db.session.add(response)
    db.session.commit()
    return response


def add_skip_rule(question, choice_label: str, target_page=None):
    """``question`` answered with ``choice_label`` jumps to ``target_page``
    (or ends the survey when no page is given)."""
    from survey_builder.models import BranchRule

    choice = next(c for c in question.choices if c.label == choice_label)
    question.branch_rules.append(BranchRule(choice=choice, target_page=target_page))
    db.session.commit()
