import pytest

from survey_builder.domain.question_types import QUESTION_TYPES
from survey_builder.domain.sharing import publish_problems
from survey_builder.domain.templates import TEMPLATES, build_from_template


@pytest.mark.parametrize("key", sorted(TEMPLATES))
def test_templates_build_publishable_surveys(key, owner, db):
    template = TEMPLATES[key]
    survey = build_from_template(template, owner.id)
    db.session.add(survey)
    db.session.commit()
    assert survey.title == template.title
    assert len(survey.questions) == template.question_count
    assert all(q.type in QUESTION_TYPES for q in survey.questions)
    assert publish_problems(survey) == []


def test_nps_template_starts_with_nps(owner, db):
    survey = build_from_template(TEMPLATES["nps"], owner.id)
    assert survey.questions[0].type == "nps"
    assert survey.questions[0].required
