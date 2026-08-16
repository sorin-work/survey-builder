from flask import Flask, g, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import models  # noqa: F401  (register models with SQLAlchemy)
from .config import load_config
from .extensions import csrf, db, login_manager, migrate

# Everything is served from our own origin. Inline handlers (confirm dialogs)
# and the per-survey accent <style> still need 'unsafe-inline'.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
)


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .account import bp as account_bp
    from .api import bp as api_bp
    from .auth import bp as auth_bp
    from .editor import bp as editor_bp
    from .public import bp as public_bp
    from .results import bp as results_bp
    from .surveys import bp as surveys_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(surveys_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(api_bp)

    from .domain.question_types import QUESTION_TYPES
    from .domain.settings import TEXT_FORMATS
    from .formatting import duration, nl2br, timeago

    app.jinja_env.globals["QUESTION_TYPES"] = QUESTION_TYPES
    app.jinja_env.globals["TEXT_FORMATS"] = TEXT_FORMATS
    app.jinja_env.filters["duration"] = duration
    app.jinja_env.filters["nl2br"] = nl2br
    app.jinja_env.filters["timeago"] = timeago

    from .domain.estimate import estimated_minutes

    app.jinja_env.globals["estimated_minutes"] = estimated_minutes

    from .cli import register_cli
    from .errors import register_error_pages
    from .logging import configure_logging

    configure_logging(app)
    register_cli(app)
    register_error_pages(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if not g.get("allow_framing"):
            response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        return response

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("surveys.dashboard"))
        return render_template("index.html")

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            app.logger.exception("health check: database unavailable")
            return {"status": "error", "database": "unavailable"}, 503
        return {"status": "ok", "database": "ok"}

    return app
