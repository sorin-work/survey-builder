"""A whole journey: build a survey, publish it, answer it, read the results."""

import csv
import io

from survey_builder.models import Question, Survey

HX = {"HX-Request": "true"}


def test_build_publish_answer_and_export(auth_client, client, owner, db):
    resp = auth_client.post("/surveys/new", data={"title": "Lunch poll"})
    survey = db.session.query(Survey).one()
    page = survey.pages[0]
    base = f"/surveys/{survey.id}"

    auth_client.post(
        f"{base}/pages/{page.id}/questions", data={"type": "single_choice"}, headers=HX
    )
    auth_client.post(f"{base}/pages/{page.id}/questions", data={"type": "rating"}, headers=HX)
    choice_q, rating_q = db.session.query(Question).order_by(Question.position).all()
    first, second = choice_q.choices
    auth_client.post(
        f"{base}/questions/{choice_q.id}",
        data={
            "prompt": "Where should we eat?",
            "required": "on",
            f"choice_{first.id}": "Pizza",
            f"choice_{second.id}": "Sushi",
        },
        headers=HX,
    )
    auth_client.post(
        f"{base}/questions/{rating_q.id}", data={"prompt": "How hungry are you?", "scale": "5"}
    )
    resp = auth_client.post(f"{base}/publish")
    assert resp.status_code == 302
    db.session.refresh(survey)
    link = f"/s/{survey.share_token}"

    for pick, hunger in ((first, 5), (second, 3), (first, 4)):
        respondent = client.application.test_client()
        assert respondent.get(link).status_code == 200
        resp = respondent.post(
            link,
            data={"page_id": page.id, f"q{choice_q.id}": pick.id, f"q{rating_q.id}": hunger},
        )
        assert resp.headers["Location"].endswith("/thanks")

    summary = auth_client.get(f"{base}/results/").get_data(as_text=True)
    assert '"counts": [2, 1], "kind": "pie", "labels": ["Pizza", "Sushi"]' in summary
    assert "Average <strong>4.0</strong>" in summary

    rows = list(
        csv.reader(
            io.StringIO(auth_client.get(f"{base}/results/export.csv").get_data(as_text=True))
        )
    )
    assert rows[0][2:] == ["Where should we eat?", "How hungry are you?"]
    assert sorted(r[2] for r in rows[1:]) == ["Pizza", "Pizza", "Sushi"]

    auth_client.post(f"{base}/close")
    assert client.application.test_client().get(link).status_code == 410
