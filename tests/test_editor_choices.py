from factories import make_survey, make_user

from survey_builder.models import Choice, Question

HX = {"HX-Request": "true"}


def choice_question(db, survey, labels=("Red", "Blue")):
    question = Question(type="single_choice", prompt="Favourite colour?")
    question.choices = [Choice(label=label, position=i) for i, label in enumerate(labels)]
    survey.pages[0].questions.append(question)
    db.session.commit()
    return question


def test_add_choice(auth_client, owner, db):
    survey = make_survey(owner)
    question = choice_question(db, survey)
    resp = auth_client.post(f"/surveys/{survey.id}/questions/{question.id}/choices", headers=HX)
    assert resp.status_code == 200
    db.session.refresh(question)
    assert [c.label for c in question.choices] == ["Red", "Blue", "Option 3"]


def test_cannot_add_choice_to_text_question(auth_client, owner, db):
    survey = make_survey(owner)
    question = Question(type="short_text", prompt="Name")
    survey.pages[0].questions.append(question)
    db.session.commit()
    resp = auth_client.post(f"/surveys/{survey.id}/questions/{question.id}/choices", headers=HX)
    assert resp.status_code == 400


def test_rename_choices_with_question(auth_client, owner, db):
    survey = make_survey(owner)
    question = choice_question(db, survey)
    red, blue = question.choices
    data = {"prompt": "Colour?", f"choice_{red.id}": "Crimson", f"choice_{blue.id}": " Navy "}
    resp = auth_client.post(f"/surveys/{survey.id}/questions/{question.id}", data=data, headers=HX)
    assert resp.status_code == 200
    db.session.refresh(question)
    assert [c.label for c in question.choices] == ["Crimson", "Navy"]


def test_duplicate_or_empty_choices_are_rejected(auth_client, owner, db):
    survey = make_survey(owner)
    question = choice_question(db, survey)
    red, blue = question.choices
    url = f"/surveys/{survey.id}/questions/{question.id}"
    data = {"prompt": "Colour?", f"choice_{red.id}": "Same", f"choice_{blue.id}": "Same"}
    resp = auth_client.post(url, data=data, headers=HX)
    assert resp.status_code == 422
    assert b"must be different" in resp.data
    data[f"choice_{blue.id}"] = ""
    assert auth_client.post(url, data=data, headers=HX).status_code == 422
    db.session.refresh(question)
    assert [c.label for c in question.choices] == ["Red", "Blue"]


def test_delete_choice_renumbers(auth_client, owner, db):
    survey = make_survey(owner)
    question = choice_question(db, survey, ("A", "B", "C"))
    first = question.choices[0]
    resp = auth_client.post(f"/surveys/{survey.id}/choices/{first.id}/delete", headers=HX)
    assert resp.status_code == 200
    db.session.refresh(question)
    assert [(c.label, c.position) for c in question.choices] == [("B", 0), ("C", 1)]


def test_last_choice_cannot_be_deleted(auth_client, owner, db):
    survey = make_survey(owner)
    question = choice_question(db, survey, ("Only",))
    only = question.choices[0]
    resp = auth_client.post(f"/surveys/{survey.id}/choices/{only.id}/delete", headers=HX)
    assert resp.status_code == 422
    assert db.session.query(Choice).count() == 1


def test_choice_of_foreign_survey_is_404(auth_client, owner, db):
    mine = make_survey(owner)
    theirs = make_survey(make_user("other@example.com"))
    question = choice_question(db, theirs)
    choice = question.choices[0]
    assert auth_client.post(f"/surveys/{mine.id}/choices/{choice.id}/delete").status_code == 404
