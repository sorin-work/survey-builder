from survey_builder.models import Choice, Page, Question, Survey, User


def make_owner(db):
    user = User(email="owner@example.com", name="Owner", password_hash="x")
    db.session.add(user)
    db.session.commit()
    return user


def test_pages_and_questions_are_ordered_by_position(db):
    owner = make_owner(db)
    survey = Survey(owner=owner, title="Feedback")
    second = Page(survey=survey, title="Second", position=1)
    first = Page(survey=survey, title="First", position=0)
    db.session.add_all([survey, second, first])
    first.questions.append(Question(type="short_text", prompt="B", position=1))
    first.questions.append(Question(type="short_text", prompt="A", position=0))
    db.session.commit()
    db.session.expire_all()

    survey = db.session.get(Survey, survey.id)
    assert [p.title for p in survey.pages] == ["First", "Second"]
    assert [q.prompt for q in survey.pages[0].questions] == ["A", "B"]


def test_new_survey_defaults(db):
    survey = Survey(owner=make_owner(db), title="Untitled")
    db.session.add(survey)
    db.session.commit()
    assert survey.status == "draft"
    assert survey.description == ""
    assert survey.created_at is not None


def test_deleting_question_removes_choices(db):
    survey = Survey(owner=make_owner(db), title="Pets")
    page = Page(survey=survey)
    question = Question(page=page, type="single_choice", prompt="Cat or dog?")
    question.choices = [Choice(label="Cat", position=0), Choice(label="Dog", position=1)]
    db.session.add(survey)
    db.session.commit()

    db.session.delete(question)
    db.session.commit()
    assert db.session.query(Choice).count() == 0
