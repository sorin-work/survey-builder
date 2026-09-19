from factories import make_published_survey

from survey_builder.domain.answers import ParsedAnswer
from survey_builder.domain.branching import next_page, valid_targets
from survey_builder.models import BranchRule


def build(owner, db):
    survey = make_published_survey(
        owner,
        [
            [
                ("single_choice", "Own a pet?", {"choices": ["Yes", "No", "Soon"]}),
                ("multiple_choice", "Which?", {"choices": ["Cat", "Dog"]}),
            ],
            [("short_text", "Pet name", {})],
            [("long_text", "Comments", {})],
        ],
    )
    return survey


def picked(question, *choices):
    return ParsedAnswer(question_id=question.id, choice_ids=[c.id for c in choices])


def test_no_rules_goes_to_next_page(owner, db):
    survey = build(owner, db)
    first, second, third = survey.pages
    assert next_page(survey, first, []) is second
    assert next_page(survey, second, []) is third
    assert next_page(survey, third, []) is None


def test_matching_rule_skips_ahead(owner, db):
    survey = build(owner, db)
    first, _, third = survey.pages
    own = first.questions[0]
    yes, no, _ = own.choices
    own.branch_rules = [BranchRule(choice=no, target_page=third)]
    db.session.commit()
    assert next_page(survey, first, [picked(own, no)]) is third
    assert next_page(survey, first, [picked(own, yes)]) is survey.pages[1]


def test_rule_can_end_the_survey(owner, db):
    survey = build(owner, db)
    first = survey.pages[0]
    own = first.questions[0]
    own.branch_rules = [BranchRule(choice=own.choices[1])]
    db.session.commit()
    assert next_page(survey, first, [picked(own, own.choices[1])]) is None


def test_first_question_with_a_match_wins(owner, db):
    survey = build(owner, db)
    first, second, third = survey.pages
    own, which = first.questions
    own.branch_rules = [BranchRule(choice=own.choices[0], target_page=second)]
    which.branch_rules = [BranchRule(choice=which.choices[1], target_page=third)]
    db.session.commit()
    answers = [picked(own, own.choices[0]), picked(which, which.choices[1])]
    assert next_page(survey, first, answers) is second
    assert next_page(survey, first, [picked(which, which.choices[1])]) is third


def test_valid_targets_are_later_pages(owner, db):
    survey = build(owner, db)
    first, second, third = survey.pages
    assert valid_targets(survey, first) == [second, third]
    assert valid_targets(survey, third) == []


def test_unreachable_pages(owner, db):
    from survey_builder.domain.branching import unreachable_pages

    survey = build(owner, db)
    first, second, third = survey.pages
    own = first.questions[0]
    assert unreachable_pages(survey) == []

    # Every answer jumps to page 3, but the question is optional: page 2 is still reachable.
    own.branch_rules = [BranchRule(choice=c, target_page=third) for c in own.choices]
    db.session.commit()
    assert unreachable_pages(survey) == []

    own.required = True
    db.session.commit()
    assert unreachable_pages(survey) == [second]


def test_editor_warns_about_unreachable_pages(auth_client, owner, db):
    survey = build(owner, db)
    first, second, third = survey.pages
    own = first.questions[0]
    own.required = True
    own.branch_rules = [BranchRule(choice=c) for c in own.choices]
    db.session.commit()
    html = auth_client.get(f"/surveys/{survey.id}/edit").get_data(as_text=True)
    assert html.count("Nobody can reach this page") == 2
