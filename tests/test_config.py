from survey_builder.config import _database_url


def test_default_database_is_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _database_url().startswith("sqlite:///")


def test_postgres_urls_use_psycopg_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db:5432/surveys")
    assert _database_url() == "postgresql+psycopg://u:p@db:5432/surveys"
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db/surveys")
    assert _database_url() == "postgresql+psycopg://u:p@db/surveys"


def test_explicit_driver_is_kept(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/surveys")
    assert _database_url() == "postgresql+psycopg://u:p@db/surveys"


def test_cookie_flags(monkeypatch):
    from survey_builder.config import load_config

    monkeypatch.delenv("SECURE_COOKIES", raising=False)
    config = load_config()
    assert config["SESSION_COOKIE_HTTPONLY"] is True
    assert config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert config["SESSION_COOKIE_SECURE"] is False
    monkeypatch.setenv("SECURE_COOKIES", "true")
    assert load_config()["SESSION_COOKIE_SECURE"] is True


def test_embedding_needs_cross_site_cookies(monkeypatch):
    from survey_builder.config import load_config

    monkeypatch.delenv("SECURE_COOKIES", raising=False)
    monkeypatch.setenv("ALLOW_EMBEDDING", "true")
    config = load_config()
    assert config["SESSION_COOKIE_SAMESITE"] == "None"
    assert config["SESSION_COOKIE_SECURE"] is True


def _external_url(trusted_proxies):
    from flask import url_for

    from survey_builder import create_app

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TRUSTED_PROXIES": trusted_proxies,
        }
    )

    @app.get("/where")
    def where():
        return url_for("public.show", token="abc", _external=True)

    headers = {"X-Forwarded-Proto": "https", "X-Forwarded-Host": "surveys.example.com"}
    return app.test_client().get("/where", headers=headers).get_data(as_text=True)


def test_forwarded_headers_are_ignored_by_default():
    assert _external_url(0) == "http://localhost/s/abc"


def test_trusted_proxy_makes_share_links_https():
    assert _external_url(1) == "https://surveys.example.com/s/abc"
