from datetime import timedelta

from factories import add_response, make_published_survey

from survey_builder.cli import prune_incomplete
from survey_builder.models import Answer, Response, utcnow


def test_prune_incomplete_keeps_recent_and_completed(owner, db):
    survey = make_published_survey(owner)
    question = survey.questions[0]
    old_draft = add_response(survey, {question: "old"}, completed=False)
    old_draft.started_at = utcnow() - timedelta(days=45)
    add_response(survey, {question: "new"}, completed=False)
    done = add_response(survey, {question: "done"})
    done.started_at = utcnow() - timedelta(days=90)
    db.session.commit()

    assert prune_incomplete(30) == 1
    assert db.session.query(Response).count() == 2
    assert db.session.query(Answer).filter_by(text_value="old").count() == 0


def test_prune_incomplete_command(app, owner, db):
    result = app.test_cli_runner().invoke(args=["prune-incomplete", "--days", "7"])
    assert "Removed 0 abandoned responses." in result.output


def test_create_user_command(app, db):
    from survey_builder.models import User

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-user", "New@Example.com", "--name", "New", "--password", "long-password"]
    )
    assert result.exit_code == 0, result.output
    user = db.session.query(User).one()
    assert user.email == "new@example.com" and user.check_password("long-password")

    again = runner.invoke(args=["create-user", "new@example.com", "--password", "long-password"])
    assert again.exit_code != 0 and "already has an account" in again.output
    short = runner.invoke(args=["create-user", "x@example.com", "--password", "short"])
    assert short.exit_code != 0
