def test_healthz_returns_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_landing_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Survey Builder" in resp.data
