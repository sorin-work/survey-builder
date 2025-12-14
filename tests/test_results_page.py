from factories import add_response, make_published_survey, make_user


def build(owner):
    return make_published_survey(
        owner,
        [
            [
                ("single_choice", "Plan", {"choices": ["Free", "Pro"]}),
                ("rating", "Support", {}),
                ("long_text", "Anything else?", {}),
                ("date", "Joined", {}),
            ]
        ],
    )


def test_results_empty_state(auth_client, owner):
    survey = build(owner)
    resp = auth_client.get(f"/surveys/{survey.id}/results/")
    assert resp.status_code == 200
    assert b"No responses yet" in resp.data


def test_results_show_counts_and_texts(auth_client, owner):
    survey = build(owner)
    plan, rating, comment, _ = survey.questions
    add_response(survey, {plan: "Pro", rating: 4, comment: "Love the export"})
    add_response(survey, {plan: "Pro", rating: 5})
    html = auth_client.get(f"/surveys/{survey.id}/results/").get_data(as_text=True)
    assert '2</span><span class="muted">completed responses' in html
    assert "Love the export" in html
    assert "100.0%" in html
    assert "Average <strong>4.5</strong>" in html


def test_results_are_owner_only(auth_client, db):
    survey = build(make_user("other@example.com"))
    assert auth_client.get(f"/surveys/{survey.id}/results/").status_code == 404
