"""Demo data: a demo account with a few surveys and realistic responses."""

import random
import secrets
from datetime import date, timedelta

from sqlalchemy import select

from .extensions import db
from .models import Answer, BranchRule, Choice, Page, Question, Response, Survey, User, utcnow

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo-password"

COMMENTS = [
    "Setup took five minutes, which was great.",
    "Support answered within the hour. Thanks!",
    "The mobile app is slow when I have many projects.",
    "Please add a dark mode.",
    "Pricing is a bit steep for small teams.",
    "Exports to CSV saved me hours every month.",
    "I would love more keyboard shortcuts.",
    "Onboarding emails were helpful.",
    "Sometimes the dashboard takes a while to load.",
    "Great product, keep it up.",
    "Integration with our calendar would be nice.",
    "The new reports are exactly what we needed.",
]


def _question(qtype, prompt, position, choices=(), **kwargs):
    question = Question(type=qtype, prompt=prompt, position=position, **kwargs)
    question.choices = [Choice(label=label, position=i) for i, label in enumerate(choices)]
    return question


def _customer_survey(owner: User) -> Survey:
    survey = Survey(
        owner=owner,
        title="Customer satisfaction 2026",
        description="Two minutes, five questions. Your answers help us decide what to build next.",
        thank_you_message="Thanks for helping us improve!",
        status="published",
        share_token=secrets.token_urlsafe(12),
    )
    about = Page(title="About you", position=0)
    about.questions = [
        _question(
            "single_choice",
            "Which plan are you on?",
            0,
            ["Free", "Starter", "Business", "Enterprise"],
            required=True,
        ),
        _question(
            "multiple_choice",
            "Which features do you use every week?",
            1,
            ["Dashboards", "Reports", "CSV export", "Integrations", "Mobile app"],
            settings={"max_choices": 3},
        ),
        _question("date", "When did you start using the product?", 2),
    ]
    opinion = Page(title="Your opinion", position=1)
    opinion.questions = [
        _question(
            "rating",
            "How satisfied are you with our support?",
            0,
            settings={"scale": 5, "low_label": "Very unhappy", "high_label": "Delighted"},
            required=True,
        ),
        _question(
            "nps",
            "How likely are you to recommend us to a friend or colleague?",
            1,
            settings={"low_label": "Not at all likely", "high_label": "Extremely likely"},
            required=True,
        ),
        _question("long_text", "Anything else you would like to tell us?", 2),
    ]
    survey.pages = [about, opinion]
    return survey


def _offsite_survey(owner: User) -> Survey:
    survey = Survey(
        owner=owner,
        title="Team offsite planning",
        description="Help us pick the dates and the activities.",
        status="published",
        share_token=secrets.token_urlsafe(12),
    )
    attend = Page(title="Attendance", position=0)
    joining = _question(
        "single_choice", "Will you join the offsite?", 1, ["Yes", "No"], required=True
    )
    attend.questions = [_question("short_text", "Your name", 0, required=True), joining]
    page = Page(title="Plans", position=1)
    page.questions = [
        _question(
            "single_choice",
            "Which week works best?",
            0,
            ["First week of June", "Second week of June", "Last week of June"],
            required=True,
        ),
        _question(
            "multiple_choice",
            "Activities you would enjoy",
            1,
            ["Hiking", "Cooking class", "Escape room", "Board games", "Kayaking"],
        ),
        _question("long_text", "Dietary requirements", 2),
    ]
    survey.pages = [attend, page]
    # People who cannot come skip the planning questions.
    joining.branch_rules = [BranchRule(choice=joining.choices[1])]
    return survey


def _draft_survey(owner: User) -> Survey:
    survey = Survey(owner=owner, title="Product feedback (draft)", description="Work in progress.")
    page = Page(position=0)
    page.questions = [_question("short_text", "What should we build next?", 0)]
    survey.pages = [page]
    return survey


def _fake_customer_responses(survey: Survey, count: int, rng: random.Random) -> None:
    plan, features, started = survey.pages[0].questions
    support, nps, comments = survey.pages[1].questions
    now = utcnow()
    for _ in range(count):
        completed = now - timedelta(days=rng.randint(0, 120), minutes=rng.randint(0, 1440))
        response = Response(
            survey=survey,
            key=secrets.token_hex(16),
            started_at=completed - timedelta(minutes=rng.randint(1, 8)),
            completed_at=completed,
        )
        answers = [Answer(question=plan, choice=rng.choices(plan.choices, [5, 3, 2, 1])[0])]
        for choice in rng.sample(features.choices, rng.randint(0, 3)):
            answers.append(Answer(question=features, choice=choice))
        if rng.random() < 0.7:
            day = date(2023, 1, 1) + timedelta(days=rng.randint(0, 1100))
            answers.append(Answer(question=started, date_value=day))
        answers.append(
            Answer(question=support, number_value=rng.choices([1, 2, 3, 4, 5], [1, 1, 3, 6, 5])[0])
        )
        answers.append(
            Answer(question=nps, number_value=rng.choices(range(11), [1] * 6 + [2, 4, 5, 6, 5])[0])
        )
        if rng.random() < 0.4:
            answers.append(Answer(question=comments, text_value=rng.choice(COMMENTS)))
        response.answers = answers
        db.session.add(response)


def _fake_offsite_responses(survey: Survey, rng: random.Random) -> None:
    name, joining = survey.pages[0].questions
    week, activities, diet = survey.pages[1].questions
    names = ["Ana", "Bogdan", "Carla", "Dan", "Elena", "Filip", "Gabi", "Horia", "Ioana"]
    for person in names:
        completed = utcnow() - timedelta(days=rng.randint(0, 10), hours=rng.randint(0, 23))
        response = Response(
            survey=survey, key=secrets.token_hex(16), started_at=completed, completed_at=completed
        )
        db.session.add(response)
        if rng.random() < 0.2:
            response.answers = [
                Answer(question=name, text_value=person),
                Answer(question=joining, choice=joining.choices[1]),
            ]
            continue
        response.answers = [
            Answer(question=name, text_value=person),
            Answer(question=joining, choice=joining.choices[0]),
            Answer(question=week, choice=rng.choice(week.choices)),
            *(
                Answer(question=activities, choice=c)
                for c in rng.sample(activities.choices, rng.randint(1, 3))
            ),
        ]
        if rng.random() < 0.3:
            response.answers.append(Answer(question=diet, text_value="Vegetarian, please."))


def seed_demo(responses: int = 140) -> bool:
    """Create the demo account and its data. Returns False if it already exists."""
    if db.session.scalar(select(User).filter_by(email=DEMO_EMAIL)):
        return False
    rng = random.Random(2026)
    owner = User(email=DEMO_EMAIL, name="Demo User")
    owner.set_password(DEMO_PASSWORD)
    customer = _customer_survey(owner)
    offsite = _offsite_survey(owner)
    draft = _draft_survey(owner)
    db.session.add_all([owner, customer, offsite, draft])
    db.session.flush()
    now = utcnow()
    customer.published_at = now - timedelta(days=121)
    offsite.published_at = now - timedelta(days=11)
    _fake_customer_responses(customer, responses, rng)
    _fake_offsite_responses(offsite, rng)
    db.session.commit()
    return True
