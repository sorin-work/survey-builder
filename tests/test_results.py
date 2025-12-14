from datetime import date

from factories import add_response, make_published_survey

from survey_builder.domain.results import completed_response_count, summarize


def build(owner):
    return make_published_survey(
        owner,
        [
            [
                ("single_choice", "Plan", {"choices": ["Free", "Pro", "Team"]}),
                ("multiple_choice", "Uses", {"choices": ["Docs", "Chat", "Video"]}),
                ("rating", "Support", {"settings": {"scale": 5}}),
                ("short_text", "Comment", {}),
                ("date", "Joined", {}),
            ]
        ],
    )


def test_choice_counts_follow_choice_order(owner, db):
    survey = build(owner)
    plan, uses, *_ = survey.questions
    add_response(survey, {plan: "Pro", uses: ["Docs", "Chat"]})
    add_response(survey, {plan: "Pro", uses: ["Docs"]})
    add_response(survey, {plan: "Free"})

    by_q = {s.question.id: s for s in summarize(survey)}
    assert by_q[plan.id].labels == ["Free", "Pro", "Team"]
    assert by_q[plan.id].counts == [1, 2, 0]
    assert by_q[plan.id].answered == 3
    assert by_q[uses.id].counts == [2, 1, 0]
    assert by_q[uses.id].answered == 2
    assert by_q[uses.id].percentages == [100.0, 50.0, 0.0]


def test_rating_distribution_and_average(owner, db):
    survey = build(owner)
    rating = survey.questions[2]
    for value in (5, 4, 4, 2):
        add_response(survey, {rating: value})
    summary = summarize(survey)[2]
    assert summary.labels == ["1", "2", "3", "4", "5"]
    assert summary.counts == [0, 1, 0, 2, 1]
    assert summary.average == 3.8


def test_text_answers_newest_first(owner, db):
    from datetime import datetime

    survey = build(owner)
    comment = survey.questions[3]
    add_response(survey, {comment: "first"}, when=datetime(2025, 12, 1, 10))
    add_response(survey, {comment: "second"}, when=datetime(2025, 12, 2, 10))
    summary = summarize(survey)[3]
    assert summary.answered == 2
    assert summary.texts == ["second", "first"]


def test_dates_grouped_by_month(owner, db):
    survey = build(owner)
    joined = survey.questions[4]
    for day in (date(2025, 1, 5), date(2025, 1, 20), date(2025, 3, 1)):
        add_response(survey, {joined: day})
    summary = summarize(survey)[4]
    assert (summary.earliest, summary.latest) == (date(2025, 1, 5), date(2025, 3, 1))
    assert summary.labels == ["2025-01", "2025-03"]
    assert summary.counts == [2, 1]


def test_incomplete_responses_are_ignored(owner, db):
    survey = build(owner)
    plan = survey.questions[0]
    add_response(survey, {plan: "Team"}, completed=False)
    add_response(survey, {plan: "Free"})
    assert summarize(survey)[0].counts == [1, 0, 0]
    assert completed_response_count(survey) == 1


def test_empty_survey_summary(owner, db):
    survey = build(owner)
    summaries = summarize(survey)
    assert all(s.answered == 0 for s in summaries)
    assert summaries[2].average is None
    assert summaries[0].percentages == [0.0, 0.0, 0.0]
