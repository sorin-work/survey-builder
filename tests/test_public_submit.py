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
