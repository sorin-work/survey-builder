import logging


def test_responses_carry_a_request_id(client):
    resp = client.get("/")
    assert len(resp.headers["X-Request-ID"]) == 32


def test_incoming_request_id_is_kept(client):
    resp = client.get("/", headers={"X-Request-ID": "abc-123"})
    assert resp.headers["X-Request-ID"] == "abc-123"


def test_overlong_request_id_is_replaced(client):
    resp = client.get("/", headers={"X-Request-ID": "x" * 200})
    assert resp.headers["X-Request-ID"] != "x" * 200


def test_requests_are_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="survey_builder.requests"):
        client.get("/login")
    (record,) = [r for r in caplog.records if r.name == "survey_builder.requests"]
    assert "GET /login 200" in record.getMessage()


def test_health_checks_are_not_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="survey_builder.requests"):
        client.get("/healthz")
    assert not [r for r in caplog.records if r.name == "survey_builder.requests"]
