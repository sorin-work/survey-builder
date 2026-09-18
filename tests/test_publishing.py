from factories import make_survey, make_user

from survey_builder.domain.sharing import publish_problems
from survey_builder.models import Question


def with_question(db, survey, qtype="short_text"):
    survey.pages[0].questions.append(Question(type=qtype, prompt="Anything else?"))
    db.session.commit()
    return survey


def test_empty_survey_cannot_be_published(auth_client, owner, db):
    survey = make_survey(owner)
    resp = auth_client.post(f"/surveys/{survey.id}/publish", follow_redirects=True)
    assert b"Add at least one question" in resp.data
    db.session.refresh(survey)
    assert survey.status == "draft"
    assert survey.share_token is None


def test_choice_question_without_options_blocks_publishing(db, owner):
    survey = with_question(db, make_survey(owner), "single_choice")
    assert publish_problems(survey) == ["“Anything else?” has no options."]


def test_publish_creates_share_token(auth_client, owner, db):
    survey = with_question(db, make_survey(owner))
    resp = auth_client.post(f"/surveys/{survey.id}/publish")
    assert resp.status_code == 302
    db.session.refresh(survey)
    assert survey.status == "published"
    assert len(survey.share_token) >= 16
    assert survey.published_at is not None


def test_close_and_reopen_keep_the_same_link(auth_client, owner, db):
    survey = with_question(db, make_survey(owner))
    auth_client.post(f"/surveys/{survey.id}/publish")
    db.session.refresh(survey)
    token = survey.share_token
    auth_client.post(f"/surveys/{survey.id}/close")
    db.session.refresh(survey)
    assert survey.status == "closed"
    auth_client.post(f"/surveys/{survey.id}/publish")
    db.session.refresh(survey)
    assert (survey.status, survey.share_token) == ("published", token)


def test_cannot_publish_someone_elses_survey(auth_client, db):
    survey = with_question(db, make_survey(make_user("other@example.com")))
    assert auth_client.post(f"/surveys/{survey.id}/publish").status_code == 404


def test_editor_shows_share_link_once_published(auth_client, owner, db):
    survey = with_question(db, make_survey(owner))
    assert b"Share link" not in auth_client.get(f"/surveys/{survey.id}/edit").data
    auth_client.post(f"/surveys/{survey.id}/publish")
    db.session.refresh(survey)
    html = auth_client.get(f"/surveys/{survey.id}/edit").get_data(as_text=True)
    assert f"http://localhost/s/{survey.share_token}" in html


def test_share_panel_shows_limit_and_close_date(auth_client, owner, db):
    from datetime import date

    from factories import add_response

    survey = with_question(db, make_survey(owner))
    auth_client.post(f"/surveys/{survey.id}/publish")
    survey.response_limit = 10
    survey.closes_on = date(2099, 6, 30)
    db.session.commit()
    add_response(survey, {survey.questions[0]: "hi"})
    html = auth_client.get(f"/surveys/{survey.id}/edit").get_data(as_text=True)
    assert "1 completed response of 10." in html
    assert "Open until the end of June 30, 2099." in html


def test_reopening_clears_a_close_date_in_the_past(auth_client, owner, db):
    from datetime import date

    survey = with_question(db, make_survey(owner))
    survey.status = "closed"
    survey.share_token = "reopen"
    survey.closes_on = date(2020, 1, 1)
    db.session.commit()
    resp = auth_client.post(f"/surveys/{survey.id}/publish", follow_redirects=True)
    assert b"close date had passed" in resp.data
    db.session.refresh(survey)
    assert survey.status == "published" and survey.closes_on is None
    assert auth_client.get("/s/reopen").status_code == 200


def test_publishing_keeps_a_future_close_date(auth_client, owner, db):
    from datetime import date

    survey = with_question(db, make_survey(owner))
    survey.closes_on = date(2099, 1, 1)
    db.session.commit()
    auth_client.post(f"/surveys/{survey.id}/publish")
    db.session.refresh(survey)
    assert survey.closes_on == date(2099, 1, 1)
