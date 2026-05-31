from factories import make_survey, make_user

from survey_builder.models import Page

HX = {"HX-Request": "true"}


def test_editor_renders_pages(auth_client, owner):
    survey = make_survey(owner, title="Team pulse")
    resp = auth_client.get(f"/surveys/{survey.id}/edit")
    assert resp.status_code == 200
    assert b"Team pulse" in resp.data
    assert b"Page 1" in resp.data


def test_editor_is_owner_only(auth_client):
    survey = make_survey(make_user("other@example.com"))
    assert auth_client.get(f"/surveys/{survey.id}/edit").status_code == 404


def test_add_page_htmx_returns_fragment(auth_client, owner, db):
    survey = make_survey(owner)
    resp = auth_client.post(f"/surveys/{survey.id}/pages", data={"title": "About you"}, headers=HX)
    assert resp.status_code == 200
    assert b"Page 2" in resp.data
    assert b"<html" not in resp.data
    assert [p.title for p in survey.pages] == ["", "About you"]


def test_add_page_without_htmx_redirects(auth_client, owner):
    survey = make_survey(owner)
    resp = auth_client.post(f"/surveys/{survey.id}/pages")
    assert resp.status_code == 302
    assert f"/surveys/{survey.id}/edit#page-" in resp.headers["Location"]


def test_rename_page(auth_client, owner, db):
    survey = make_survey(owner)
    page = survey.pages[0]
    auth_client.post(f"/surveys/{survey.id}/pages/{page.id}", data={"title": " Intro "}, headers=HX)
    db.session.refresh(page)
    assert page.title == "Intro"


def test_delete_page_renumbers(auth_client, owner, db):
    survey = make_survey(owner)
    for title in ("B", "C"):
        survey.pages.append(Page(title=title, position=len(survey.pages)))
    db.session.commit()
    first = survey.pages[0]
    resp = auth_client.post(f"/surveys/{survey.id}/pages/{first.id}/delete", headers=HX)
    assert resp.status_code == 200
    db.session.refresh(survey)
    assert [(p.title, p.position) for p in survey.pages] == [("B", 0), ("C", 1)]


def test_cannot_delete_last_page(auth_client, owner, db):
    survey = make_survey(owner)
    page = survey.pages[0]
    auth_client.post(f"/surveys/{survey.id}/pages/{page.id}/delete")
    assert db.session.query(Page).count() == 1


def test_page_from_another_survey_is_404(auth_client, owner):
    mine = make_survey(owner)
    theirs = make_survey(make_user("other@example.com"))
    other_page = theirs.pages[0]
    resp = auth_client.post(f"/surveys/{mine.id}/pages/{other_page.id}", data={"title": "x"})
    assert resp.status_code == 404


def test_move_page_down_and_up(auth_client, owner, db):
    survey = make_survey(owner)
    survey.pages[0].title = "A"
    for title in ("B", "C"):
        survey.pages.append(Page(title=title, position=len(survey.pages)))
    db.session.commit()
    a = survey.pages[0]
    url = f"/surveys/{survey.id}/pages/{a.id}/move"

    resp = auth_client.post(url, data={"direction": "down"}, headers=HX)
    assert resp.status_code == 204
    db.session.expire_all()
    assert [p.title for p in survey.pages] == ["B", "A", "C"]

    auth_client.post(url, data={"direction": "up"}, headers=HX)
    auth_client.post(url, data={"direction": "up"}, headers=HX)
    db.session.expire_all()
    assert [(p.title, p.position) for p in survey.pages] == [("A", 0), ("B", 1), ("C", 2)]


def test_move_page_rejects_bad_direction(auth_client, owner):
    survey = make_survey(owner)
    page = survey.pages[0]
    resp = auth_client.post(f"/surveys/{survey.id}/pages/{page.id}/move", data={"direction": "x"})
    assert resp.status_code == 400


def test_page_description_is_saved_and_shown_to_respondents(auth_client, client, owner, db):
    from factories import make_published_survey

    survey = make_published_survey(owner)
    page = survey.pages[0]
    auth_client.post(
        f"/surveys/{survey.id}/pages/{page.id}",
        data={"title": "About you", "description": "Takes a minute."},
        headers=HX,
    )
    db.session.refresh(page)
    assert page.description == "Takes a minute."
    html = client.application.test_client().get(f"/s/{survey.share_token}").get_data(as_text=True)
    assert "Takes a minute." in html
