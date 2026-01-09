import csv
import io
from datetime import date, datetime

from factories import add_response, make_published_survey

from survey_builder.domain.export import export_rows, to_csv


def build(owner):
    return make_published_survey(
        owner,
        [
            [
                ("short_text", "Name", {}),
                ("multiple_choice", "Pets", {"choices": ["Cat", "Dog", "Fish"]}),
            ],
            [("nps", "Recommend", {}), ("date", "Visited", {})],
        ],
    )


def test_header_and_rows(owner, db):
    survey = build(owner)
    name, pets, nps, visited = survey.questions
    first = add_response(
        survey,
        {name: "Ana", pets: ["Cat", "Fish"], nps: 9, visited: date(2026, 1, 2)},
        when=datetime(2026, 1, 5, 9, 30),
    )
    second = add_response(survey, {name: "Bo"}, when=datetime(2026, 1, 6, 18, 0))

    rows = list(export_rows(survey))
    assert rows[0] == ["response_id", "submitted_at", "Name", "Pets", "Recommend", "Visited"]
    assert rows[1] == [str(first.id), "2026-01-05 09:30:00", "Ana", "Cat; Fish", "9", "2026-01-02"]
    assert rows[2] == [str(second.id), "2026-01-06 18:00:00", "Bo", "", "", ""]


def test_incomplete_responses_are_not_exported(owner, db):
    survey = build(owner)
    add_response(survey, {survey.questions[0]: "Half"}, completed=False)
    assert len(list(export_rows(survey))) == 1


def test_csv_quotes_commas_and_newlines(owner, db):
    survey = build(owner)
    add_response(survey, {survey.questions[0]: 'Pop, Ana "the cat"\nsecond line'})
    parsed = list(csv.reader(io.StringIO(to_csv(survey))))
    assert parsed[1][2] == 'Pop, Ana "the cat"\nsecond line'


def test_download_csv(auth_client, owner, db):
    survey = build(owner)
    add_response(survey, {survey.questions[0]: "Ana"})
    resp = auth_client.get(f"/surveys/{survey.id}/results/export.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert 'filename="customer-feedback-responses.csv"' in resp.headers["Content-Disposition"]
    assert "Ana" in resp.get_data(as_text=True)


def test_download_csv_is_owner_only(auth_client, db):
    from factories import make_user

    survey = build(make_user("other@example.com"))
    assert auth_client.get(f"/surveys/{survey.id}/results/export.csv").status_code == 404
