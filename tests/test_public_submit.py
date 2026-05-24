from factories import make_published_survey

from survey_builder.models import Answer, Response


def two_page_survey(owner):
    return make_published_survey(
        owner,
        [
            [
                ("short_text", "Name", {"required": True}),
                ("multiple_choice", "Pets", {"choices": ["Cat", "Dog", "Fish"]}),
            ],
            [("nps", "Recommend us?", {}), ("date", "Visited on", {})],
        ],
    )


def ids(survey):
    page1, page2 = survey.pages
    name, pets = page1.questions
    nps, visited = page2.questions
    return page1, page2, name, pets, nps, visited


def test_submitting_both_pages_completes_the_response(client, owner, db):
    survey = two_page_survey(owner)
    page1, page2, name, pets, nps, visited = ids(survey)
    url = f"/s/{survey.share_token}"

    resp = client.post(
        url,
        data={
            "page_id": page1.id,
            f"q{name.id}": "Ana",
            f"q{pets.id}": [pets.choices[0].id, pets.choices[2].id],
        },
    )
    assert resp.status_code == 302
    response = db.session.query(Response).one()
    assert response.completed_at is None

    assert "Page 2 of 2" in client.get(url).get_data(as_text=True)

    resp = client.post(
        url, data={"page_id": page2.id, f"q{nps.id}": "9", f"q{visited.id}": "2025-11-30"}
    )
    assert resp.headers["Location"].endswith("/thanks")
    db.session.refresh(response)
    assert response.completed_at is not None

    answers = db.session.query(Answer).filter_by(response_id=response.id).all()
    assert sorted(a.question_id for a in answers) == sorted(
        [name.id, pets.id, pets.id, nps.id, visited.id]
    )
    assert client.get(url).headers["Location"].endswith("/thanks")


def test_validation_errors_keep_values(client, owner, db):
    survey = two_page_survey(owner)
    page1, _, name, pets, _, _ = ids(survey)
    resp = client.post(
        f"/s/{survey.share_token}",
        data={"page_id": page1.id, f"q{pets.id}": pets.choices[1].id},
    )
    assert resp.status_code == 422
    html = resp.get_data(as_text=True)
    assert "This question is required." in html
    assert f'value="{pets.choices[1].id}"\n                   checked' in html
    assert db.session.query(Response).count() == 0


def test_stale_page_submission_is_ignored(client, owner, db):
    survey = two_page_survey(owner)
    page1, page2, name, *_ = ids(survey)
    url = f"/s/{survey.share_token}"
    resp = client.post(url, data={"page_id": page2.id})
    assert resp.status_code == 302
    assert db.session.query(Response).count() == 0


def test_skipped_optional_questions_store_nothing(client, owner, db):
    survey = make_published_survey(owner, [[("long_text", "Comments", {})]])
    page = survey.pages[0]
    client.post(f"/s/{survey.share_token}", data={"page_id": page.id})
    assert db.session.query(Response).one().is_complete
    assert db.session.query(Answer).count() == 0


def test_closed_survey_rejects_submissions(client, owner, db):
    survey = two_page_survey(owner)
    survey.status = "closed"
    db.session.commit()
    resp = client.post(f"/s/{survey.share_token}", data={"page_id": survey.pages[0].id})
    assert resp.status_code == 410


def test_back_returns_to_previous_page_with_saved_answers(client, owner, db):
    survey = two_page_survey(owner)
    page1, page2, name, pets, *_ = ids(survey)
    url = f"/s/{survey.share_token}"
    client.post(url, data={"page_id": page1.id, f"q{name.id}": "Ana"})
    assert b"Back" in client.get(url).data

    resp = client.post(f"{url}/back")
    assert resp.status_code == 302
    html = client.get(url).get_data(as_text=True)
    assert "Page 1 of 2" in html
    assert 'value="Ana"' in html


def test_back_on_first_page_does_nothing(client, owner):
    survey = two_page_survey(owner)
    url = f"/s/{survey.share_token}"
    client.post(f"{url}/back")
    assert "Page 1 of 2" in client.get(url).get_data(as_text=True)


def test_branch_rule_skips_a_page(client, owner, db):
    from survey_builder.models import BranchRule

    survey = make_published_survey(
        owner,
        [
            [("single_choice", "Own a pet?", {"choices": ["Yes", "No"]})],
            [("short_text", "Pet name", {})],
            [("long_text", "Comments", {})],
        ],
    )
    first, second, third = survey.pages
    own = first.questions[0]
    own.branch_rules = [BranchRule(choice=own.choices[1], target_page=third)]
    db.session.commit()
    url = f"/s/{survey.share_token}"

    client.post(url, data={"page_id": first.id, f"q{own.id}": own.choices[1].id})
    assert "Page 3 of 3" in client.get(url).get_data(as_text=True)
    resp = client.post(url, data={"page_id": third.id})
    assert resp.headers["Location"].endswith("/thanks")


def test_branch_rule_can_end_the_survey_early(client, owner, db):
    from survey_builder.models import BranchRule

    survey = two_page_survey(owner)
    page1, _, name, pets, *_ = ids(survey)
    pets.branch_rules = [BranchRule(choice=pets.choices[2])]
    db.session.commit()
    resp = client.post(
        f"/s/{survey.share_token}",
        data={"page_id": page1.id, f"q{name.id}": "Ana", f"q{pets.id}": pets.choices[2].id},
    )
    assert resp.headers["Location"].endswith("/thanks")
    assert db.session.query(Response).one().is_complete


def test_resubmitting_a_page_after_back_replaces_its_answers(client, owner, db):
    survey = two_page_survey(owner)
    page1, page2, name, pets, nps, _ = ids(survey)
    url = f"/s/{survey.share_token}"
    cat, dog, fish = pets.choices

    client.post(url, data={"page_id": page1.id, f"q{name.id}": "Ana", f"q{pets.id}": [cat.id]})
    client.post(f"{url}/back")
    client.post(
        url, data={"page_id": page1.id, f"q{name.id}": "Ana Pop", f"q{pets.id}": [dog.id, fish.id]}
    )
    client.post(url, data={"page_id": page2.id, f"q{nps.id}": "10"})

    answers = db.session.query(Answer).all()
    assert sorted((a.question_id, a.text_value, a.choice_id) for a in answers) == sorted(
        [
            (name.id, "Ana Pop", None),
            (pets.id, None, dog.id),
            (pets.id, None, fish.id),
            (nps.id, None, None),
        ]
    )


def test_errors_are_linked_to_their_question_for_screen_readers(client, owner):
    survey = make_published_survey(
        owner,
        [[("short_text", "Name", {"required": True, "help_text": "First name is fine"})]],
        title="A11y",
    )
    question = survey.questions[0]
    resp = client.post(f"/s/{survey.share_token}", data={"page_id": survey.pages[0].id})
    html = resp.get_data(as_text=True)
    assert 'aria-invalid="true"' in html
    assert f'aria-describedby="q{question.id}-help q{question.id}-error"' in html
    assert f'id="q{question.id}-error"' in html


def test_progress_cookie_outlives_the_browser_session(client, owner):
    survey = two_page_survey(owner)
    page1, _, name, *_ = ids(survey)
    resp = client.post(f"/s/{survey.share_token}", data={"page_id": page1.id, f"q{name.id}": "Ana"})
    cookie = resp.headers["Set-Cookie"]
    assert "Expires=" in cookie
