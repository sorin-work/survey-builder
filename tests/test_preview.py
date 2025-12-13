from factories import make_published_survey, make_user

from survey_builder.models import Response


def survey_for(owner):
    return make_published_survey(
        owner,
        [[("short_text", "Name", {"required": True})], [("nps", "Recommend?", {})]],
    )


def test_preview_shows_first_page_with_banner(auth_client, owner):
    survey = survey_for(owner)
    resp = auth_client.get(f"/surveys/{survey.id}/preview")
    assert resp.status_code == 200
    assert b"Preview" in resp.data
    assert b"Page 1 of 2" in resp.data


def test_preview_validates_and_moves_on_without_saving(auth_client, owner, db):
    survey = survey_for(owner)
    name = survey.pages[0].questions[0]
    url = f"/surveys/{survey.id}/preview"
    assert auth_client.post(url, data={}).status_code == 422
    resp = auth_client.post(url, data={f"q{name.id}": "Ana"})
    assert resp.headers["Location"].endswith("preview?page=2")
    resp = auth_client.post(f"{url}?page=2", data={})
    assert resp.headers["Location"].endswith(f"/surveys/{survey.id}/edit")
    assert db.session.query(Response).count() == 0


def test_preview_is_owner_only(auth_client):
    survey = survey_for(make_user("other@example.com"))
    assert auth_client.get(f"/surveys/{survey.id}/preview").status_code == 404


def test_preview_clamps_page_number(auth_client, owner):
    survey = survey_for(owner)
    resp = auth_client.get(f"/surveys/{survey.id}/preview?page=99")
    assert b"Page 2 of 2" in resp.data
