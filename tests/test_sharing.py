from datetime import date, datetime

from factories import add_response, make_published_survey

from survey_builder.domain.sharing import closed_reason, is_accepting_responses


def test_published_survey_without_limits_is_open(owner, db):
    survey = make_published_survey(owner)
    assert closed_reason(survey) is None


def test_closed_and_draft_surveys(owner, db):
    survey = make_published_survey(owner)
    survey.status = "closed"
    assert closed_reason(survey) == "closed"
    survey.status = "draft"
    assert closed_reason(survey) == "draft"


def test_close_date_in_the_past_closes_the_survey(owner, db):
    survey = make_published_survey(owner)
    survey.closes_on = date(2026, 1, 10)
    assert closed_reason(survey, now=datetime(2026, 1, 20, 9, 0)) == "date"
    assert is_accepting_responses(survey, now=datetime(2026, 1, 5, 9, 0))


def test_response_limit(owner, db):
    survey = make_published_survey(owner)
    survey.response_limit = 3
    question = survey.questions[0]
    add_response(survey, {question: "one"})
    assert is_accepting_responses(survey)
    for value in ("two", "three", "four", "five"):
        add_response(survey, {question: value})
    assert closed_reason(survey) == "limit"


def test_incomplete_responses_do_not_count_towards_limit(owner, db):
    survey = make_published_survey(owner)
    survey.response_limit = 1
    for _ in range(3):
        add_response(survey, {survey.questions[0]: "x"}, completed=False)
    assert is_accepting_responses(survey)


def test_survey_stays_open_for_the_whole_close_date(owner, db):
    survey = make_published_survey(owner)
    survey.closes_on = date(2026, 3, 10)
    assert is_accepting_responses(survey, now=datetime(2026, 3, 10, 0, 0))
    assert is_accepting_responses(survey, now=datetime(2026, 3, 10, 23, 59, 59))
    assert closed_reason(survey, now=datetime(2026, 3, 11, 0, 0)) == "date"


def test_limit_closes_the_survey_exactly_when_reached(owner, db):
    survey = make_published_survey(owner)
    survey.response_limit = 2
    question = survey.questions[0]
    add_response(survey, {question: "one"})
    assert is_accepting_responses(survey)
    add_response(survey, {question: "two"})
    assert closed_reason(survey) == "limit"


def test_no_response_beyond_the_limit_through_the_public_form(client, owner, db):
    from survey_builder.models import Response

    survey = make_published_survey(owner)
    survey.response_limit = 1
    db.session.commit()
    page = survey.pages[0]
    question = survey.questions[0]
    first = client.application.test_client()
    second = client.application.test_client()
    first.post(f"/s/{survey.share_token}", data={"page_id": page.id, f"q{question.id}": "a"})
    resp = second.post(
        f"/s/{survey.share_token}", data={"page_id": page.id, f"q{question.id}": "b"}
    )
    assert resp.status_code == 410
    assert db.session.query(Response).filter(Response.completed_at.is_not(None)).count() == 1
