from datetime import date

from factories import make_survey

from survey_builder.models import Answer, Choice, Question, Response


def test_response_with_answers(db, owner):
    survey = make_survey(owner)
    page = survey.pages[0]
    text_q = Question(type="short_text", prompt="Name")
    multi_q = Question(type="multiple_choice", prompt="Pets")
    multi_q.choices = [Choice(label="Cat", position=0), Choice(label="Dog", position=1)]
    date_q = Question(type="date", prompt="Birthday")
    page.questions = [text_q, multi_q, date_q]
    db.session.commit()

    response = Response(survey=survey, key="abc123")
    db.session.add(response)
    response.answers = [
        Answer(question=text_q, text_value="Ana"),
        Answer(question=multi_q, choice=multi_q.choices[0]),
        Answer(question=multi_q, choice=multi_q.choices[1]),
        Answer(question=date_q, date_value=date(1990, 5, 17)),
    ]
    db.session.add(response)
    db.session.commit()
    db.session.expire_all()

    response = db.session.get(Response, response.id)
    assert not response.is_complete
    assert len(response.answers) == 4
    assert {a.choice.label for a in response.answers if a.choice} == {"Cat", "Dog"}


def test_deleting_survey_removes_responses(db, owner):
    survey = make_survey(owner)
    db.session.add(Response(survey=survey, key="k1"))
    db.session.commit()
    db.session.delete(survey)
    db.session.commit()
    assert db.session.query(Response).count() == 0
