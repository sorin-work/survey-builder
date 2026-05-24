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


def test_new_survey_page_lists_templates(auth_client):
    html = auth_client.get("/surveys/new").get_data(as_text=True)
    assert "Or start from a template" in html
    assert all(t.title in html for t in TEMPLATES.values())


def test_create_from_template(auth_client, owner, db):
    from survey_builder.models import Survey

    resp = auth_client.post("/surveys/new/from-template", data={"template": "event"})
    assert resp.status_code == 302
    survey = db.session.query(Survey).one()
    assert survey.owner_id == owner.id
    assert survey.title == "Event feedback"
    assert len(survey.pages) == 2


def test_unknown_template(auth_client, db):
    assert auth_client.post("/surveys/new/from-template", data={"template": "x"}).status_code == 400
