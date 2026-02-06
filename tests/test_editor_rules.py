from factories import make_published_survey, make_user

from survey_builder.models import BranchRule

HX = {"HX-Request": "true"}


def build(owner, title="Pets"):
    return make_published_survey(
        owner,
        [
            [("single_choice", "Own a pet?", {"choices": ["Yes", "No"]})],
            [("short_text", "Pet name", {})],
            [("long_text", "Comments", {})],
        ],
        title=title,
    )


def add_rule(client, survey, question, choice, target):
    return client.post(
        f"/surveys/{survey.id}/questions/{question.id}/rules",
        data={"choice_id": choice.id, "target": target},
        headers=HX,
    )


def test_add_skip_rule(auth_client, owner, db):
    survey = build(owner)
    question = survey.questions[0]
    third = survey.pages[2]
    resp = add_rule(auth_client, survey, question, question.choices[1], third.id)
    assert resp.status_code == 200
    assert "go to page 3" in resp.get_data(as_text=True)
    rule = db.session.query(BranchRule).one()
    assert (rule.choice_id, rule.target_page_id) == (question.choices[1].id, third.id)


def test_add_end_rule_and_replace_it(auth_client, owner, db):
    survey = build(owner)
    question = survey.questions[0]
    no = question.choices[1]
    add_rule(auth_client, survey, question, no, "end")
    assert db.session.query(BranchRule).one().ends_survey
    add_rule(auth_client, survey, question, no, survey.pages[1].id)
    rule = db.session.query(BranchRule).one()
    assert rule.target_page_id == survey.pages[1].id


def test_rule_cannot_point_backwards(auth_client, owner, db):
    survey = build(owner)
    name = survey.pages[1].questions[0]
    name.type = "single_choice"
    from survey_builder.models import Choice

    name.choices = [Choice(label="Rex", position=0)]
    db.session.commit()
    resp = add_rule(auth_client, survey, name, name.choices[0], survey.pages[0].id)
    assert resp.status_code == 422
    assert db.session.query(BranchRule).count() == 0


def test_rule_needs_an_option_of_the_question(auth_client, owner, db):
    survey = build(owner)
    question = survey.questions[0]
    other = build(make_user("other@example.com"), title="Other")
    foreign_choice = other.questions[0].choices[0]
    resp = add_rule(auth_client, survey, question, foreign_choice, "end")
    assert resp.status_code == 422


def test_rules_only_for_choice_questions(auth_client, owner, db):
    survey = build(owner)
    text = survey.pages[1].questions[0]
    resp = auth_client.post(
        f"/surveys/{survey.id}/questions/{text.id}/rules", data={"target": "end"}, headers=HX
    )
    assert resp.status_code == 400


def test_delete_rule(auth_client, owner, db):
    survey = build(owner)
    question = survey.questions[0]
    add_rule(auth_client, survey, question, question.choices[0], "end")
    rule = db.session.query(BranchRule).one()
    resp = auth_client.post(f"/surveys/{survey.id}/rules/{rule.id}/delete", headers=HX)
    assert resp.status_code == 200
    assert db.session.query(BranchRule).count() == 0


def test_moving_pages_drops_rules_that_now_point_backwards(auth_client, owner, db):
    survey = build(owner)
    question = survey.questions[0]
    first, second, third = survey.pages
    add_rule(auth_client, survey, question, question.choices[0], second.id)
    add_rule(auth_client, survey, question, question.choices[1], third.id)

    # Move page 2 above page 1: the rule to it would now jump backwards.
    auth_client.post(f"/surveys/{survey.id}/pages/{second.id}/move", data={"direction": "up"})
    db.session.expire_all()
    rules = db.session.query(BranchRule).all()
    assert [r.target_page_id for r in rules] == [third.id]


def test_moving_a_question_to_a_later_page_drops_its_broken_rules(auth_client, owner, db):
    survey = build(owner)
    question = survey.questions[0]
    second, third = survey.pages[1], survey.pages[2]
    add_rule(auth_client, survey, question, question.choices[0], second.id)
    auth_client.post(
        f"/surveys/{survey.id}/questions/{question.id}/page", data={"page_id": third.id}
    )
    assert db.session.query(BranchRule).count() == 0
