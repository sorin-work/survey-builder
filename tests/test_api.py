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


def test_responses_endpoint_paginates(auth_client, owner):
    from datetime import date

    survey = make_published_survey(
        owner,
        [
            [
                ("short_text", "Name", {}),
                ("multiple_choice", "Pets", {"choices": ["Cat", "Dog"]}),
                ("date", "Since", {}),
            ]
        ],
        title="API",
    )
    name, pets, since = survey.questions
    add_response(survey, {name: "Ana", pets: ["Cat", "Dog"], since: date(2024, 1, 2)})
    for i in range(3):
        add_response(survey, {name: f"r{i}"})
    data = auth_client.get(f"/api/surveys/{survey.id}/responses?per_page=2").get_json()
    assert (data["total"], data["pages"], data["page"]) == (4, 2, 1)
    first = data["responses"][0]["answers"]
    assert first == {str(name.id): "Ana", str(pets.id): ["Cat", "Dog"], str(since.id): "2024-01-02"}
    page2 = auth_client.get(f"/api/surveys/{survey.id}/responses?per_page=2&page=2").get_json()
    assert [r["answers"][str(name.id)] for r in page2["responses"]] == ["r1", "r2"]
    assert page2["responses"][0]["answers"][str(pets.id)] is None


def test_responses_endpoint_is_owner_only(auth_client):
    survey = make_published_survey(make_user("other@example.com"))
    assert auth_client.get(f"/api/surveys/{survey.id}/responses").status_code == 404


def test_summary_accepts_period_and_segment(auth_client, owner):
    from datetime import datetime

    survey = make_published_survey(
        owner,
        [[("single_choice", "Plan", {"choices": ["Free", "Pro"]}), ("rating", "Ease", {})]],
        title="Filters",
    )
    plan, ease = survey.questions
    add_response(survey, {plan: "Free", ease: 2}, when=datetime(2026, 8, 1))
    add_response(survey, {plan: "Pro", ease: 4}, when=datetime(2026, 9, 1))
    add_response(survey, {plan: "Pro", ease: 5}, when=datetime(2026, 9, 2))

    url = f"/api/surveys/{survey.id}/summary"
    data = auth_client.get(f"{url}?from=2026-09-01").get_json()
    assert data["responses"]["completed"] == 2
    data = auth_client.get(f"{url}?choice={plan.choices[0].id}").get_json()
    assert data["questions"][1]["average"] == 2.0
    assert data["questions"][1]["median"] == 2.0
