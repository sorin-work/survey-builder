from flask import Flask, render_template

from . import models  # noqa: F401  (register models with SQLAlchemy)
from .config import load_config
from .extensions import db, migrate


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
