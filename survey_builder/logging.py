"""Request ids and one log line per request."""

import logging
import time
import uuid

from flask import Flask, g, request

logger = logging.getLogger("survey_builder.requests")


def configure_logging(app: Flask) -> None:
    if not app.debug and not app.testing:
        logging.basicConfig(
            level=app.config.get("LOG_LEVEL", "INFO"),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )

    @app.before_request
    def start_timer():
        incoming = request.headers.get("X-Request-ID", "")
        g.request_id = incoming if 0 < len(incoming) <= 64 else uuid.uuid4().hex
        g.started = time.perf_counter()

    @app.after_request
    def log_request(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        if request.path.startswith("/static/") or request.path == "/healthz":
            return response
        elapsed = (time.perf_counter() - g.get("started", time.perf_counter())) * 1000
        logger.info(
            "%s %s %s %.1fms request_id=%s",
            request.method,
            request.path,
            response.status_code,
            elapsed,
            request_id,
        )
        return response
