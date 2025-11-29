import re

import pytest

from survey_builder import create_app
from survey_builder.extensions import db


@pytest.fixture
def csrf_client():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "WTF_CSRF_ENABLED": True}
    )
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def test_post_without_token_is_rejected(csrf_client):
    resp = csrf_client.post("/login", data={"email": "a@example.com", "password": "x"})
    assert resp.status_code == 400


def test_forms_carry_a_token(csrf_client):
    page = csrf_client.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    resp = csrf_client.post(
        "/login", data={"email": "a@example.com", "password": "x", "csrf_token": token}
    )
    assert resp.status_code == 401


def test_htmx_header_token_is_accepted(csrf_client):
    page = csrf_client.get("/login").get_data(as_text=True)
    token = re.search(r'"X-CSRFToken": "([^"]+)"', page).group(1)
    resp = csrf_client.post(
        "/login", data={"email": "a@example.com", "password": "x"}, headers={"X-CSRFToken": token}
    )
    assert resp.status_code == 401
