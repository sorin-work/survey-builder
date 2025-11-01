import os


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///survey_builder.db")
    # Heroku-style URLs and plain postgresql:// should use the psycopg 3 driver.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def load_config() -> dict:
    return {
        "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        "SQLALCHEMY_DATABASE_URI": _database_url(),
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
    }
