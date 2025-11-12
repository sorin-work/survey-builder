from survey_builder.auth import validate_registration
from survey_builder.models import User


def register(client, **overrides):
    data = {"name": "Ana Pop", "email": "ana@example.com", "password": "s3cret-pass"}
    data.update(overrides)
    return client.post("/register", data=data)


def test_register_form_renders(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"Create an account" in resp.data


def test_register_creates_user_and_logs_in(client, db):
    resp = register(client, email="  Ana@Example.COM ")
    assert resp.status_code == 302
    user = db.session.query(User).one()
    assert user.email == "ana@example.com"
    assert user.check_password("s3cret-pass")
    with client.session_transaction() as sess:
        assert sess["_user_id"] == str(user.id)


def test_register_rejects_duplicate_email(client, db):
    register(client)
    other = client.application.test_client()
    resp = register(other, name="Other")
    assert resp.status_code == 422
    assert b"already exists" in resp.data
    assert db.session.query(User).count() == 1


def test_validate_registration_messages():
    errors = validate_registration("", "not-an-email", "short")
    assert set(errors) == {"name", "email", "password"}
    assert validate_registration("Ana", "ana@example.com", "longenough") == {}


def test_login_with_valid_credentials(client):
    register(client)
    client.post("/logout")
    resp = client.post("/login", data={"email": "ANA@example.com", "password": "s3cret-pass"})
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert "_user_id" in sess


def test_login_with_wrong_password(client):
    register(client)
    client.post("/logout")
    resp = client.post("/login", data={"email": "ana@example.com", "password": "nope"})
    assert resp.status_code == 401
    assert b"incorrect" in resp.data


def test_login_redirects_to_safe_next_only(client):
    register(client)
    client.post("/logout")
    creds = {"email": "ana@example.com", "password": "s3cret-pass"}
    resp = client.post("/login?next=/surveys", data=creds)
    assert resp.headers["Location"] == "/surveys"
    client.post("/logout")
    resp = client.post("/login?next=//evil.example.com", data=creds)
    assert resp.headers["Location"] == "/"


def test_logout_requires_post(client):
    register(client)
    assert client.get("/logout").status_code == 405
