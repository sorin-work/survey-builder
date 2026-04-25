from dataclasses import dataclass

from survey_builder.domain.estimate import estimated_minutes


@dataclass
class Q:
    type: str


def test_empty_survey_takes_no_time():
    assert estimated_minutes([]) == 0


def test_short_surveys_round_up_to_a_minute():
    assert estimated_minutes([Q("nps")]) == 1


def test_estimate_adds_up_question_types():
    questions = [Q("long_text"), Q("long_text"), Q("short_text"), Q("rating"), Q("nps")]
    assert estimated_minutes(questions) == 3  # 152 seconds


def test_editor_header_shows_counts(auth_client, owner):
    from factories import make_published_survey

    survey = make_published_survey(owner, [[("long_text", "A", {})], [("nps", "B", {})]])
    html = auth_client.get(f"/surveys/{survey.id}/edit").get_data(as_text=True)
    assert "2 questions on 2 pages" in html
    assert "about 2 min to complete" in html
