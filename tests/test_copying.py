from factories import add_response, make_published_survey, make_user

from survey_builder.models import Survey


def build(owner):
    return make_published_survey(
        owner,
        [
            [("single_choice", "Plan", {"choices": ["Free", "Pro"], "required": True})],
            [("rating", "Support", {"settings": {"scale": 7}, "help_text": "1 is bad"})],
        ],
        title="Original",
    )


def test_duplicate_copies_structure_but_not_responses(auth_client, owner, db):
    survey = build(owner)
    add_response(survey, {survey.questions[0]: "Pro"})
    resp = auth_client.post(f"/surveys/{survey.id}/duplicate")
    assert resp.status_code == 302

    clone = db.session.query(Survey).filter(Survey.id != survey.id).one()
    assert clone.title == "Copy of Original"
    assert clone.status == "draft"
    assert clone.share_token is None
    assert clone.responses == []
    assert [len(p.questions) for p in clone.pages] == [1, 1]
    plan, support = clone.questions
    assert [c.label for c in plan.choices] == ["Free", "Pro"]
    assert plan.required is True
    assert support.settings == {"scale": 7}
    assert support.help_text == "1 is bad"
    assert {q.id for q in clone.questions}.isdisjoint({q.id for q in survey.questions})


def test_duplicate_settings_are_independent(auth_client, owner, db):
    survey = build(owner)
    auth_client.post(f"/surveys/{survey.id}/duplicate")
    clone = db.session.query(Survey).filter(Survey.id != survey.id).one()
    clone.questions[1].settings["scale"] = 3
    assert survey.questions[1].settings == {"scale": 7}


def test_cannot_duplicate_foreign_survey(auth_client, db):
    survey = build(make_user("other@example.com"))
    assert auth_client.post(f"/surveys/{survey.id}/duplicate").status_code == 404
