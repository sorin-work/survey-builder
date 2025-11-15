from survey_builder.extensions import db
from survey_builder.models import Page, Survey, User

PASSWORD = "s3cret-pass"


def make_user(email="owner@example.com", name="Owner") -> User:
    user = User(email=email, name=name)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def make_survey(owner: User, title="Customer feedback", **kwargs) -> Survey:
    survey = Survey(owner=owner, title=title, **kwargs)
    survey.pages.append(Page(position=0))
    db.session.add(survey)
    db.session.commit()
    return survey


def login(client, user: User) -> None:
    resp = client.post("/login", data={"email": user.email, "password": PASSWORD})
    assert resp.status_code == 302
