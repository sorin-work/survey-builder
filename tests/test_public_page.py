from factories import make_published_survey, make_survey


def test_unknown_token_is_404(client, db):
    assert client.get("/s/nope").status_code == 404


def test_draft_survey_is_not_public(client, owner, db):
    survey = make_survey(owner)
    survey.share_token = "draft-token"
    db.session.commit()
    assert client.get("/s/draft-token").status_code == 404


def test_closed_survey_shows_message(client, owner, db):
    survey = make_published_survey(owner)
    survey.status = "closed"
    db.session.commit()
    resp = client.get(f"/s/{survey.share_token}")
    assert resp.status_code == 410
    assert b"no longer accepting responses" in resp.data


def test_renders_every_question_type(client, owner):
    survey = make_published_survey(
        owner,
        [
            [
                ("short_text", "Name", {"required": True}),
                ("long_text", "Tell us more", {"help_text": "Be honest"}),
                ("single_choice", "Plan", {"choices": ["Free", "Pro"]}),
                ("multiple_choice", "Features", {"choices": ["Export", "Charts"]}),
                ("rating", "Support", {"settings": {"scale": 4}}),
                ("nps", "Recommend", {}),
                ("date", "Start date", {}),
            ]
        ],
    )
    html = client.get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert 'type="text"' in html and "<textarea" in html
    assert 'type="radio"' in html and 'type="checkbox"' in html
    assert "Be honest" in html
    assert 'value="4"' in html and 'type="date"' in html
    nps = survey.pages[0].questions[5]
    assert html.count(f'name="q{nps.id}"') == 11
    assert "Submit" in html


def test_multi_page_survey_shows_progress(client, owner):
    survey = make_published_survey(
        owner, [[("short_text", "A", {})], [("short_text", "B", {})]], title="Two pages"
    )
    html = client.get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert "Page 1 of 2" in html
    assert "Next" in html


def test_closed_page_explains_close_date(client, owner, db):
    from datetime import date

    survey = make_published_survey(owner)
    survey.closes_on = date(2025, 12, 31)
    db.session.commit()
    resp = client.get(f"/s/{survey.share_token}")
    assert resp.status_code == 410
    assert b"closed on December 31, 2025" in resp.data


def test_closed_page_explains_limit(client, owner, db):
    from factories import add_response

    survey = make_published_survey(owner)
    survey.response_limit = 1
    for value in ("a", "b"):
        add_response(survey, {survey.questions[0]: value})
    resp = client.get(f"/s/{survey.share_token}")
    assert resp.status_code == 410
    assert b"all the responses it needed" in resp.data


def test_text_fields_get_a_character_counter(client, owner):
    survey = make_published_survey(
        owner, [[("long_text", "Story", {"settings": {"max_length": 300}})]]
    )
    question = survey.questions[0]
    html = client.get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert f'data-counter="q{question.id}-count"' in html
    assert f'id="q{question.id}-count"' in html
    assert "js/public.js" in html


def test_progress_bar_reflects_the_page(client, owner):
    survey = make_published_survey(
        owner,
        [[("short_text", "A", {})], [("short_text", "B", {})], [("short_text", "C", {})]],
        title="Three pages",
    )
    html = client.get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert 'aria-valuenow="0"' in html
    first = survey.pages[0]
    client.post(f"/s/{survey.share_token}", data={"page_id": first.id})
    html = client.get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert 'aria-valuenow="33"' in html


def test_email_questions_use_an_email_input(client, owner):
    survey = make_published_survey(
        owner, [[("short_text", "Email", {"settings": {"format": "email"}})]], title="Emails"
    )
    html = client.get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert 'type="email"' in html


def test_questions_are_numbered_across_pages(client, owner, db):
    survey = make_published_survey(
        owner,
        [[("short_text", "A", {}), ("short_text", "B", {})], [("short_text", "C", {})]],
        title="Numbered",
    )
    html = client.get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert '<span class="question-number">2.</span>' in html
    client.post(f"/s/{survey.share_token}", data={"page_id": survey.pages[0].id})
    html = client.get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert '<span class="question-number">3.</span>' in html
