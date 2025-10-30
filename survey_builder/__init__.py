from flask import Flask


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY="dev")
    if config:
        app.config.update(config)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
