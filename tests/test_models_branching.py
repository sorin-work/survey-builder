from factories import make_published_survey

from survey_builder.models import BranchRule


def build(owner):
    return make_published_survey(
        owner,
        [
            [("single_choice", "Do you own a pet?", {"choices": ["Yes", "No"]})],
            [("short_text", "Pet name", {})],
            [("long_text", "Comments", {})],
        ],
    )


def test_rule_targets_a_page_or_the_end(owner, db):
    survey = build(owner)
    question = survey.questions[0]
    yes, no = question.choices
    question.branch_rules = [
        BranchRule(choice=no, target_page=survey.pages[2]),
        BranchRule(choice=yes),
    ]
    db.session.commit()
    db.session.expire_all()
    skip, end = question.branch_rules
    assert skip.target_page.id == survey.pages[2].id and not skip.ends_survey
    assert end.ends_survey


def test_rules_disappear_with_their_choice_or_target(owner, db):
    survey = build(owner)
    question = survey.questions[0]
    yes, no = question.choices
    question.branch_rules = [
        BranchRule(choice=no, target_page=survey.pages[2]),
        BranchRule(choice=yes, target_page=survey.pages[1]),
    ]
    db.session.commit()

    db.session.delete(survey.pages[2])
    db.session.commit()
    assert db.session.query(BranchRule).count() == 1

    question.choices.remove(yes)
    db.session.commit()
    assert db.session.query(BranchRule).count() == 0
