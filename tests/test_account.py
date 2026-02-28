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
