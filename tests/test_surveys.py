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
