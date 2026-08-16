from sqlalchemy.exc import OperationalError


def test_healthz_returns_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "database": "ok"}


def test_healthz_reports_database_problems(client, db, monkeypatch):
    def broken(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(db.session, "execute", broken)
    resp = client.get("/healthz")
    assert resp.status_code == 503
    assert resp.get_json()["database"] == "unavailable"


def test_landing_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Survey Builder" in resp.data


def test_security_headers(client):
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "same-origin"


def test_static_assets_are_served(client):
    for path in ("css/app.css", "img/favicon.svg", "vendor/htmx.min.js", "vendor/chart.umd.min.js"):
        assert client.get(f"/static/{path}").status_code == 200


def test_content_security_policy(client):
    policy = client.get("/").headers["Content-Security-Policy"]
    assert "default-src 'self'" in policy
    assert "object-src 'none'" in policy
