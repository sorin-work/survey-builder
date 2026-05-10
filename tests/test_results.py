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


def test_period_filter_is_inclusive_of_both_days(owner, db):
    from datetime import datetime

    from survey_builder.domain.results import ResponseFilter

    survey = build(owner)
    plan = survey.questions[0]
    add_response(survey, {plan: "Free"}, when=datetime(2026, 1, 31, 23, 59))
    add_response(survey, {plan: "Pro"}, when=datetime(2026, 2, 1, 0, 0))
    add_response(survey, {plan: "Team"}, when=datetime(2026, 2, 28, 23, 59))
    add_response(survey, {plan: "Team"}, when=datetime(2026, 3, 1, 0, 1))

    february = ResponseFilter(date(2026, 2, 1), date(2026, 2, 28))
    assert completed_response_count(survey, february) == 2
    assert summarize(survey, february)[0].counts == [0, 1, 1]
    assert completed_response_count(survey, ResponseFilter(end=date(2026, 1, 31))) == 1


def test_period_from_query_args_ignores_garbage():
    from survey_builder.domain.results import ResponseFilter

    period = ResponseFilter.from_args({"from": "2026-02-01", "to": "soon"})
    assert period == ResponseFilter(date(2026, 2, 1), None)
    assert period.as_args() == {"from": "2026-02-01"}
    assert ResponseFilter.from_args({}).is_open


def test_daily_counts_fill_gaps(owner, db):
    from datetime import datetime

    from survey_builder.domain.results import daily_counts

    survey = build(owner)
    plan = survey.questions[0]
    add_response(survey, {plan: "Free"}, when=datetime(2026, 2, 1, 9))
    add_response(survey, {plan: "Free"}, when=datetime(2026, 2, 1, 18))
    add_response(survey, {plan: "Pro"}, when=datetime(2026, 2, 4, 7))
    assert daily_counts(survey) == [
        (date(2026, 2, 1), 2),
        (date(2026, 2, 2), 0),
        (date(2026, 2, 3), 0),
        (date(2026, 2, 4), 1),
    ]


def test_daily_counts_empty(owner, db):
    from survey_builder.domain.results import daily_counts

    assert daily_counts(build(owner)) == []


def test_funnel_completion_rate_and_median(owner, db):
    from datetime import datetime, timedelta

    from survey_builder.domain.results import funnel

    survey = build(owner)
    plan = survey.questions[0]
    for minutes in (2, 4, 10):
        response = add_response(survey, {plan: "Free"}, when=datetime(2026, 2, 1, 12))
        response.started_at = response.completed_at - timedelta(minutes=minutes)
    add_response(survey, {plan: "Pro"}, completed=False)
    db.session.commit()
    result = funnel(survey)
    assert (result.started, result.completed) == (4, 3)
    assert result.completion_rate == 75
    assert result.median_seconds == 240


def test_funnel_without_responses(owner, db):
    from survey_builder.domain.results import funnel

    result = funnel(build(owner))
    assert result.completion_rate is None and result.median_seconds is None


def test_segment_only_counts_respondents_who_picked_the_choice(owner, db):
    from survey_builder.domain.results import ResponseFilter

    survey = build(owner)
    plan, uses, rating, *_ = survey.questions
    free, pro, _ = plan.choices
    add_response(survey, {plan: "Pro", rating: 5})
    add_response(survey, {plan: "Pro", rating: 3})
    add_response(survey, {plan: "Free", rating: 1})

    pro_only = ResponseFilter(choice_id=pro.id)
    assert completed_response_count(survey, pro_only) == 2
    summaries = summarize(survey, pro_only)
    assert summaries[2].average == 4.0
    assert summaries[0].counts == [0, 2, 0]
    assert ResponseFilter.from_args({"choice": str(free.id)}).choice_id == free.id
    assert ResponseFilter.from_args({"choice": "x"}).choice_id is None
