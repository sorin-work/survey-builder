from factories import add_response, make_published_survey, make_user


def test_api_requires_login(client, db):
    resp = client.get("/api/surveys")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "authentication required"}


def test_list_own_surveys(auth_client, owner):
    mine = make_published_survey(owner, title="Mine")
    make_published_survey(make_user("other@example.com"), title="Theirs")
    data = auth_client.get("/api/surveys").get_json()
    assert [s["id"] for s in data["surveys"]] == [mine.id]
    assert data["surveys"][0]["status"] == "published"


def test_summary(auth_client, owner):
    survey = make_published_survey(
        owner,
        [[("single_choice", "Plan", {"choices": ["Free", "Pro"]}), ("nps", "Recommend", {})]],
    )
    plan, nps = survey.questions
    add_response(survey, {plan: "Pro", nps: 10})
    add_response(survey, {plan: "Free", nps: 9})
    data = auth_client.get(f"/api/surveys/{survey.id}/summary").get_json()
    assert data["responses"]["completed"] == 2
    first, second = data["questions"]
    assert first["labels"] == ["Free", "Pro"] and first["counts"] == [1, 1]
    assert second["nps"]["score"] == 100


def test_summary_of_foreign_survey_is_404(auth_client, db):
    survey = make_published_survey(make_user("other@example.com"))
    resp = auth_client.get(f"/api/surveys/{survey.id}/summary")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "not found"}
