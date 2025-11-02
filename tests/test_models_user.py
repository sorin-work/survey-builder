from survey_builder.models import User


def test_password_is_hashed_and_checked(db):
    user = User(email="ana@example.com", name="Ana")
    user.set_password("correct horse")
    db.session.add(user)
    db.session.commit()

    assert user.password_hash != "correct horse"
    assert user.check_password("correct horse")
    assert not user.check_password("wrong")


def test_created_at_is_set(db):
    user = User(email="bo@example.com", name="Bo", password_hash="x")
    db.session.add(user)
    db.session.commit()
    assert user.created_at is not None
