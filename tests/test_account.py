from factories import make_user

from survey_builder.models import User


def test_profile_requires_login(client):
    assert client.get("/account/").status_code == 302


def test_update_name_and_email(auth_client, owner, db):
    resp = auth_client.post("/account/", data={"name": "New Name", "email": "NEW@example.com"})
    assert resp.status_code == 302
    db.session.refresh(owner)
    assert (owner.name, owner.email) == ("New Name", "new@example.com")


def test_email_must_be_unique(auth_client, owner, db):
    make_user("taken@example.com", name="Taken")
    resp = auth_client.post("/account/", data={"name": "Owner", "email": "taken@example.com"})
    assert resp.status_code == 422
    assert b"already exists" in resp.data


def test_keeping_the_same_email_is_fine(auth_client, owner):
    resp = auth_client.post("/account/", data={"name": "Owner 2", "email": owner.email})
    assert resp.status_code == 302


def test_invalid_profile(auth_client, db):
    resp = auth_client.post("/account/", data={"name": "", "email": "nope"})
    assert resp.status_code == 422
    assert db.session.query(User).one().name == "Owner"


def change(client, current="s3cret-pass", new="brand-new-pass", confirm=None):
    return client.post(
        "/account/password",
        data={
            "current_password": current,
            "new_password": new,
            "confirm_password": new if confirm is None else confirm,
        },
    )


def test_change_password(auth_client, owner, db):
    assert change(auth_client).status_code == 302
    db.session.refresh(owner)
    assert owner.check_password("brand-new-pass")


def test_change_password_checks_current_password(auth_client, owner, db):
    resp = change(auth_client, current="wrong")
    assert resp.status_code == 422
    assert b"not your current password" in resp.data


def test_change_password_rules(auth_client):
    assert b"at least 8" in change(auth_client, new="short").data
    assert b"do not match" in change(auth_client, confirm="something-else").data


def test_delete_account_removes_surveys(auth_client, owner, db):
    from factories import add_response, make_published_survey

    from survey_builder.models import Response, Survey

    survey = make_published_survey(owner)
    add_response(survey, {survey.questions[0]: "x"})
    resp = auth_client.post("/account/delete", data={"password": "s3cret-pass"})
    assert resp.status_code == 302
    assert db.session.query(User).count() == 0
    assert db.session.query(Survey).count() == 0
    assert db.session.query(Response).count() == 0
    assert auth_client.get("/surveys/").status_code == 302


def test_delete_account_needs_password(auth_client, db):
    auth_client.post("/account/delete", data={"password": "wrong"})
    assert db.session.query(User).count() == 1


def test_changing_password_signs_out_other_devices(auth_client, owner, db):
    from factories import login

    other_device = auth_client.application.test_client()
    login(other_device, owner)
    assert other_device.get("/surveys/").status_code == 200

    assert change(auth_client).status_code == 302
    assert auth_client.get("/surveys/").status_code == 200
    assert other_device.get("/surveys/").status_code == 302
