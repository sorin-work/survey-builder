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
