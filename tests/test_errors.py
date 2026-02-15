def test_not_found_page(client):
    resp = client.get("/no/such/page")
    assert resp.status_code == 404
    assert b"Page not found" in resp.data
    assert b"<html" in resp.data


def test_htmx_errors_are_plain_text(auth_client):
    resp = auth_client.post("/surveys/999/pages", headers={"HX-Request": "true"})
    assert resp.status_code == 404
    assert b"<html" not in resp.data


def test_server_error_page(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/boom")
    def boom():
        raise RuntimeError("boom")

    resp = client.get("/boom")
    assert resp.status_code == 500
    assert b"Something went wrong" in resp.data
