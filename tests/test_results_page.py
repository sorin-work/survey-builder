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


def test_charts_carry_their_data(auth_client, owner):
    import json
    import re

    survey = build(owner)
    plan = survey.questions[0]
    add_response(survey, {plan: "Free"})
    html = auth_client.get(f"/surveys/{survey.id}/results/").get_data(as_text=True)
    specs = [json.loads(m) for m in re.findall(r"data-chart='([^']+)'", html)]
    assert {"kind": "pie", "labels": ["Free", "Pro"], "counts": [1, 0]} in specs
    assert "chart.umd.min.js" in html


def test_results_page_filters_by_period(auth_client, owner):
    from datetime import datetime

    survey = build(owner)
    plan = survey.questions[0]
    add_response(survey, {plan: "Free"}, when=datetime(2026, 1, 10, 12))
    add_response(survey, {plan: "Pro"}, when=datetime(2026, 2, 10, 12))
    html = auth_client.get(f"/surveys/{survey.id}/results/?from=2026-02-01&to=2026-02-28").get_data(
        as_text=True
    )
    assert "completed responses matching the filter" in html
    assert '"counts": [0, 1]' in html


def test_long_answers_keep_line_breaks(auth_client, owner):
    survey = build(owner)
    comment = survey.questions[2]
    add_response(survey, {comment: "Great tool.\nWould buy again."})
    html = auth_client.get(f"/surveys/{survey.id}/results/").get_data(as_text=True)
    assert "Great tool.<br>Would buy again." in html


def test_all_text_answers_page(auth_client, owner):
    survey = build(owner)
    comment = survey.questions[2]
    for i in range(12):
        add_response(survey, {comment: f"comment {i}"})
    html = auth_client.get(f"/surveys/{survey.id}/results/").get_data(as_text=True)
    assert "See all 12 answers" in html
    resp = auth_client.get(f"/surveys/{survey.id}/results/questions/{comment.id}")
    assert resp.status_code == 200
    page = resp.get_data(as_text=True)
    assert "12 answers" in page
    assert all(f"comment {i}" in page for i in range(12))


def test_text_answers_page_only_for_text_questions(auth_client, owner):
    survey = build(owner)
    plan = survey.questions[0]
    assert auth_client.get(f"/surveys/{survey.id}/results/questions/{plan.id}").status_code == 404


def test_text_answers_page_is_owner_only(auth_client, owner):
    other = build(make_user("other@example.com"))
    comment = other.questions[2]
    mine = make_published_survey(owner, title="Mine")
    url = f"/surveys/{mine.id}/results/questions/{comment.id}"
    assert auth_client.get(url).status_code == 404


def test_results_page_segment_selector(auth_client, owner):
    survey = build(owner)
    plan, rating, *_ = survey.questions
    free, pro = plan.choices
    add_response(survey, {plan: "Free", rating: 2})
    add_response(survey, {plan: "Pro", rating: 5})
    html = auth_client.get(f"/surveys/{survey.id}/results/?choice={pro.id}").get_data(as_text=True)
    assert f'<option value="{pro.id}" selected>Pro</option>' in html
    assert "Average <strong>5.0</strong>" in html
    assert f"export.csv?choice={pro.id}" in html
