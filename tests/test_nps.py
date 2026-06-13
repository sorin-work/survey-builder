from factories import add_response, make_published_survey

from survey_builder.domain.results import nps_score, summarize


def test_groups_follow_the_standard_cutoffs():
    score = nps_score([0, 6, 7, 8, 9, 10])
    assert (score.promoters, score.passives, score.detractors) == (2, 2, 2)


def test_score_range():
    assert nps_score([10, 10, 9]).score == 100
    assert nps_score([0, 3, 6]).score == -100
    assert nps_score([7, 8]).score == 0


def test_score_with_mixed_answers():
    # 5 promoters, 3 passives, 2 detractors -> 50% - 20% = 30
    assert nps_score([9] * 5 + [7] * 3 + [2] * 2).score == 30


def test_no_answers_has_no_score():
    assert nps_score([]).score is None


def test_summary_includes_nps(owner, db):
    survey = make_published_survey(owner, [[("nps", "Recommend us?", {})]])
    question = survey.questions[0]
    for value in (10, 9, 8, 3):
        add_response(survey, {question: value})
    summary = summarize(survey)[0]
    assert summary.nps.score == 25
    assert summary.counts[10] == 1


def test_results_page_shows_nps(auth_client, owner):
    survey = make_published_survey(owner, [[("nps", "Recommend us?", {})]])
    question = survey.questions[0]
    add_response(survey, {question: 10})
    html = auth_client.get(f"/surveys/{survey.id}/results/").get_data(as_text=True)
    assert '<span class="stat-value">100</span><span class="muted">NPS</span>' in html
    assert "Promoters 1" in html


def test_score_is_rounded_not_floored():
    # 1 promoter, 2 detractors: -33.3 -> -33 (floor division gave -34)
    assert nps_score([10, 0, 0]).score == -33
    # 2 promoters, 1 detractor: 33.3 -> 33
    assert nps_score([10, 10, 0]).score == 33
    # 2 promoters, 1 passive: 66.7 -> 67
    assert nps_score([10, 9, 7]).score == 67
    # 1 detractor, 2 passives: -33.3 -> -33
    assert nps_score([5, 7, 8]).score == -33
    # Halves round away from zero: 1 promoter, 7 others (12.5) -> 13, and -12.5 -> -13
    assert nps_score([10] + [7] * 7).score == 13
    assert nps_score([0] + [7] * 7).score == -13


def test_nps_by_month(owner, db):
    from datetime import datetime

    from survey_builder.domain.results import nps_by_month

    survey = make_published_survey(owner, [[("nps", "Recommend us?", {})]], title="Trend")
    question = survey.questions[0]
    for when, value in [
        (datetime(2026, 4, 3), 10),
        (datetime(2026, 4, 20), 2),
        (datetime(2026, 5, 1), 9),
        (datetime(2026, 5, 31, 23, 59), 9),
    ]:
        add_response(survey, {question: value}, when=when)
    trend = nps_by_month(survey, question)
    assert [(month, score.score) for month, score in trend] == [("2026-04", 0), ("2026-05", 100)]


def test_results_page_shows_nps_trend(auth_client, owner):
    from datetime import datetime

    survey = make_published_survey(owner, [[("nps", "Recommend us?", {})]], title="Trend page")
    question = survey.questions[0]
    add_response(survey, {question: 10}, when=datetime(2026, 4, 3))
    add_response(survey, {question: 0}, when=datetime(2026, 5, 3))
    html = auth_client.get(f"/surveys/{survey.id}/results/").get_data(as_text=True)
    assert "NPS by month" in html
    assert '"counts": [100, -100]' in html
