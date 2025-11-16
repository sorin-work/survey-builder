from factories import make_survey, make_user

from survey_builder.models import Question

HX = {"HX-Request": "true"}


def add_question(client, survey, qtype, page=None):
    page = page or survey.pages[0]
    return client.post(
        f"/surveys/{survey.id}/pages/{page.id}/questions", data={"type": qtype}, headers=HX
    )


def test_add_short_text_question(auth_client, owner, db):
    survey = make_survey(owner)
    resp = add_question(auth_client, survey, "short_text")
    assert resp.status_code == 200
    question = db.session.query(Question).one()
    assert question.type == "short_text"
    assert question.settings == {"max_length": 200}
    assert question.choices == []


def test_choice_question_gets_two_options(auth_client, owner, db):
    survey = make_survey(owner)
    resp = add_question(auth_client, survey, "single_choice")
    question = db.session.query(Question).one()
    assert [c.label for c in question.choices] == ["Option 1", "Option 2"]
    assert b"Option 2" in resp.data


def test_questions_are_appended_in_order(auth_client, owner, db):
    survey = make_survey(owner)
    for qtype in ("short_text", "rating", "nps"):
        add_question(auth_client, survey, qtype)
    assert [(q.type, q.position) for q in survey.pages[0].questions] == [
        ("short_text", 0),
        ("rating", 1),
        ("nps", 2),
    ]


def test_unknown_question_type_is_rejected(auth_client, owner, db):
    survey = make_survey(owner)
    assert add_question(auth_client, survey, "slider").status_code == 400
    assert db.session.query(Question).count() == 0


def test_cannot_add_question_to_foreign_survey(auth_client):
    survey = make_survey(make_user("other@example.com"))
    assert add_question(auth_client, survey, "short_text").status_code == 404


def test_editor_lists_existing_questions(auth_client, owner):
    survey = make_survey(owner)
    add_question(auth_client, survey, "date")
    resp = auth_client.get(f"/surveys/{survey.id}/edit")
    assert b"Untitled question" in resp.data
