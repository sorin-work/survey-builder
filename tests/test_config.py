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
