from flask import Flask, redirect, render_template, url_for
from flask_login import current_user

from . import models  # noqa: F401  (register models with SQLAlchemy)
from .config import load_config
from .extensions import csrf, db, login_manager, migrate


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .auth import bp as auth_bp
    from .editor import bp as editor_bp
    from .public import bp as public_bp
    from .results import bp as results_bp
    from .surveys import bp as surveys_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(surveys_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(results_bp)

    from .domain.question_types import QUESTION_TYPES

    app.jinja_env.globals["QUESTION_TYPES"] = QUESTION_TYPES

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("surveys.dashboard"))
        return render_template("index.html")

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
