import os
from datetime import timedelta


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///survey_builder.db")
    # Heroku-style URLs and plain postgresql:// should use the psycopg 3 driver.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def load_config() -> dict:
    secure_cookies = _flag("SECURE_COOKIES")
    return {
        "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO").upper(),
        "SQLALCHEMY_DATABASE_URI": _database_url(),
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
        "PERMANENT_SESSION_LIFETIME": timedelta(days=7),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": secure_cookies,
        "REMEMBER_COOKIE_HTTPONLY": True,
        "REMEMBER_COOKIE_SAMESITE": "Lax",
        "REMEMBER_COOKIE_SECURE": secure_cookies,
    }
