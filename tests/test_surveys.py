from factories import make_survey, make_user

from survey_builder.models import Survey


def test_dashboard_requires_login(client):
    resp = client.get("/surveys/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_dashboard_empty_state(auth_client):
    resp = auth_client.get("/surveys/")
    assert resp.status_code == 200
    assert b"You have no surveys yet" in resp.data


def test_dashboard_lists_only_own_surveys(auth_client, owner):
    make_survey(owner, title="Mine")
    make_survey(make_user("other@example.com"), title="Theirs")
    resp = auth_client.get("/surveys/")
    assert b"Mine" in resp.data
    assert b"Theirs" not in resp.data


def test_create_survey(auth_client, owner, db):
    resp = auth_client.post("/surveys/new", data={"title": " Onboarding ", "description": ""})
    assert resp.status_code == 302
    survey = db.session.query(Survey).one()
    assert survey.title == "Onboarding"
    assert survey.owner_id == owner.id
    assert len(survey.pages) == 1


def test_create_survey_requires_title(auth_client, db):
    resp = auth_client.post("/surveys/new", data={"title": "   "})
    assert resp.status_code == 422
    assert db.session.query(Survey).count() == 0


def test_index_redirects_signed_in_users(auth_client):
    resp = auth_client.get("/")
    assert resp.headers["Location"] == "/surveys/"


def test_edit_survey_details(auth_client, owner, db):
    survey = make_survey(owner, title="Old")
    resp = auth_client.post(
        f"/surveys/{survey.id}/settings", data={"title": "New", "description": "Hi"}
    )
    assert resp.status_code == 302
    db.session.refresh(survey)
    assert (survey.title, survey.description) == ("New", "Hi")


def test_cannot_edit_someone_elses_survey(auth_client, db):
    survey = make_survey(make_user("other@example.com"), title="Theirs")
    assert auth_client.get(f"/surveys/{survey.id}/settings").status_code == 404
    resp = auth_client.post(f"/surveys/{survey.id}/settings", data={"title": "Hacked"})
    assert resp.status_code == 404


def test_delete_survey(auth_client, owner, db):
    survey = make_survey(owner)
    resp = auth_client.post(f"/surveys/{survey.id}/delete")
    assert resp.status_code == 302
    assert db.session.query(Survey).count() == 0


def test_cannot_delete_someone_elses_survey(auth_client, db):
    survey = make_survey(make_user("other@example.com"))
    assert auth_client.post(f"/surveys/{survey.id}/delete").status_code == 404
    assert db.session.query(Survey).count() == 1


def test_custom_thank_you_message(auth_client, owner, db, client):
    from factories import make_published_survey

    survey = make_published_survey(owner)
    auth_client.post(
        f"/surveys/{survey.id}/settings",
        data={"title": survey.title, "thank_you_message": "See you at the meetup!"},
    )
    db.session.refresh(survey)
    assert survey.thank_you_message == "See you at the meetup!"
    resp = auth_client.get(f"/s/{survey.share_token}/thanks")
    assert b"See you at the meetup!" in resp.data


def test_thank_you_message_length_is_limited(auth_client, owner):
    survey = make_survey(owner)
    resp = auth_client.post(
        f"/surveys/{survey.id}/settings", data={"title": "T", "thank_you_message": "x" * 2001}
    )
    assert resp.status_code == 422


def test_dashboard_shows_completed_response_counts(auth_client, owner):
    from factories import add_response, make_published_survey

    survey = make_published_survey(owner, title="Counted")
    question = survey.questions[0]
    add_response(survey, {question: "a"})
    add_response(survey, {question: "b"})
    add_response(survey, {question: "c"}, completed=False)
    make_survey(owner, title="Quiet")
    html = auth_client.get("/surveys/").get_data(as_text=True)
    assert "2 responses" in html
    assert "0 responses" in html


def test_save_close_date_and_limit(auth_client, owner, db):
    from datetime import date

    survey = make_survey(owner)
    resp = auth_client.post(
        f"/surveys/{survey.id}/settings",
        data={"title": "T", "closes_on": "2026-03-01", "response_limit": "50"},
    )
    assert resp.status_code == 302
    db.session.refresh(survey)
    assert survey.closes_on == date(2026, 3, 1)
    assert survey.response_limit == 50

    auth_client.post(f"/surveys/{survey.id}/settings", data={"title": "T"})
    db.session.refresh(survey)
    assert survey.closes_on is None and survey.response_limit is None


def test_invalid_share_settings(auth_client, owner):
    survey = make_survey(owner)
    url = f"/surveys/{survey.id}/settings"
    resp = auth_client.post(url, data={"title": "T", "closes_on": "next week"})
    assert resp.status_code == 422
    resp = auth_client.post(url, data={"title": "T", "response_limit": "0"})
    assert resp.status_code == 422
    assert b"at least 1" in resp.data


def test_dashboard_search_and_status_filter(auth_client, owner, db):
    make_survey(owner, title="Customer onboarding")
    make_survey(owner, title="Team lunch", status="published")
    make_survey(owner, title="Customer churn", status="closed")

    html = auth_client.get("/surveys/?q=customer").get_data(as_text=True)
    assert "Customer onboarding" in html and "Customer churn" in html
    assert "Team lunch" not in html

    html = auth_client.get("/surveys/?q=customer&status=closed").get_data(as_text=True)
    assert "Customer churn" in html and "Customer onboarding" not in html

    html = auth_client.get("/surveys/?q=nothing-like-this").get_data(as_text=True)
    assert "No surveys match your filters" in html
