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


def test_export_respects_the_period(auth_client, owner, db):
    survey = build(owner)
    name = survey.questions[0]
    add_response(survey, {name: "January"}, when=datetime(2026, 1, 15, 8))
    add_response(survey, {name: "February"}, when=datetime(2026, 2, 15, 8))
    resp = auth_client.get(f"/surveys/{survey.id}/results/export.csv?from=2026-02-01")
    body = resp.get_data(as_text=True)
    assert "February" in body and "January" not in body
    html = auth_client.get(f"/surveys/{survey.id}/results/?from=2026-02-01").get_data(as_text=True)
    assert "export.csv?from=2026-02-01" in html


def test_columns_follow_the_survey_order_after_moving_questions(auth_client, owner, db):
    survey = build(owner)
    name, pets, nps, visited = survey.questions
    # Move "Name" to the end of the second page, then "Visited" to the top of it.
    auth_client.post(
        f"/surveys/{survey.id}/questions/{name.id}/page", data={"page_id": survey.pages[1].id}
    )
    auth_client.post(f"/surveys/{survey.id}/questions/{visited.id}/move", data={"direction": "up"})
    db.session.expire_all()
    add_response(survey, {name: "Ana", pets: "Dog", nps: 7, visited: date(2026, 3, 1)})

    header, row = list(export_rows(survey))
    assert header[2:] == [q.prompt for q in survey.questions]
    assert header[2:] == ["Pets", "Visited", "Recommend", "Name"]
    assert row[2:] == ["Dog", "2026-03-01", "7", "Ana"]


def test_formula_like_answers_are_neutralised(owner, db):
    survey = make_published_survey(
        owner,
        [[("short_text", "=Prompt", {}), ("single_choice", "Pick", {"choices": ["@SUM(A1)"]})]],
        title="Injection",
    )
    text, pick = survey.questions
    add_response(survey, {text: '=HYPERLINK("http://evil.example","click")', pick: "@SUM(A1)"})
    add_response(survey, {text: "-2+3"})
    add_response(survey, {text: "plain text - with dash"})
    header, *rows = list(export_rows(survey))
    assert header[2] == "'=Prompt"
    assert rows[0][2:] == ['\'=HYPERLINK("http://evil.example","click")', "'@SUM(A1)"]
    assert rows[1][2] == "'-2+3"
    assert rows[2][2] == "plain text - with dash"


def test_numbers_are_not_prefixed(owner, db):
    survey = make_published_survey(owner, [[("nps", "Score", {})]], title="Numbers")
    add_response(survey, {survey.questions[0]: 0})
    assert list(export_rows(survey))[1][2] == "0"


def test_download_is_utf8_with_bom_for_excel(auth_client, owner, db):
    survey = build(owner)
    add_response(survey, {survey.questions[0]: "Ștefan Pătrașcu — café"})
    resp = auth_client.get(f"/surveys/{survey.id}/results/export.csv")
    assert resp.data.startswith(b"\xef\xbb\xbf")
    assert "Ștefan Pătrașcu — café" in resp.data.decode("utf-8-sig")
