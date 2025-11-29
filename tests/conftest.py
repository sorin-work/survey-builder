import os

import pytest
from flask import g

from survey_builder import create_app
from survey_builder.extensions import db as _db


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": os.environ.get("TEST_DATABASE_URL", "sqlite://"),
            "SECRET_KEY": "test",
            "WTF_CSRF_ENABLED": False,
            # scrypt is deliberately slow; the tests do not need that.
            "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",
        }
    )

    # The app context stays pushed for the whole test, so ``g`` would be
    # shared between requests. Drop the user Flask-Login cached there.
    @app.before_request
    def _forget_cached_user():
        g.pop("_login_user", None)

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def owner(db):
    from factories import make_user

    return make_user()


@pytest.fixture
def auth_client(client, owner):
    from factories import login

    login(client, owner)
    return client
