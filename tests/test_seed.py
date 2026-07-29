from survey_builder.domain.results import completed_response_count, summarize
from survey_builder.models import Survey, User
from survey_builder.seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo


def test_seed_creates_demo_account_once(db):
    assert seed_demo(responses=20) is True
    assert seed_demo(responses=20) is False
    user = db.session.query(User).filter_by(email=DEMO_EMAIL).one()
    assert user.check_password(DEMO_PASSWORD)
    assert db.session.query(Survey).count() == 4


def test_seeded_surveys_have_results(db):
    seed_demo(responses=30)
    customer = db.session.query(Survey).filter_by(title="Customer satisfaction 2026").one()
    assert completed_response_count(customer) == 30
    summaries = summarize(customer)
    nps = next(s for s in summaries if s.question.type == "nps")
    assert nps.nps.total == 30


def test_seed_cli_command(app, db):
    result = app.test_cli_runner().invoke(args=["seed-demo", "--responses", "5"])
    assert "Demo data created" in result.output
    result = app.test_cli_runner().invoke(args=["seed-demo"])
    assert "already exists" in result.output


def test_offsite_survey_has_a_skip_rule(db):
    seed_demo(responses=1)
    offsite = db.session.query(Survey).filter_by(title="Team offsite planning").one()
    joining = offsite.pages[0].questions[1]
    (rule,) = joining.branch_rules
    assert rule.choice.label == "No" and rule.ends_survey
    assert completed_response_count(offsite) == 9


def test_event_survey_is_closed_by_date(db):
    from survey_builder.domain.sharing import closed_reason

    seed_demo(responses=1)
    event = db.session.query(Survey).filter_by(title="Spring meetup feedback").one()
    assert closed_reason(event) == "date"
    assert completed_response_count(event) == 36
