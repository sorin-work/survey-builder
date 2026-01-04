from factories import add_response, make_published_survey, make_user


def test_responses_list_empty(auth_client, owner):
    survey = make_published_survey(owner)
    resp = auth_client.get(f"/surveys/{survey.id}/results/responses")
    assert resp.status_code == 200
    assert b"No completed responses yet" in resp.data


def test_responses_list_shows_completed_only(auth_client, owner):
    survey = make_published_survey(owner)
    question = survey.questions[0]
    done = add_response(survey, {question: "Ana"})
    add_response(survey, {question: "Bo"}, completed=False)
    html = auth_client.get(f"/surveys/{survey.id}/results/responses").get_data(as_text=True)
    assert f'/responses/{done.id}">{done.id}</a>' in html
    assert html.count("<tr>") == 2  # header + one response


def test_responses_list_paginates(auth_client, owner):
    survey = make_published_survey(owner)
    question = survey.questions[0]
    for i in range(50):
        add_response(survey, {question: f"r{i}"})
    html = auth_client.get(f"/surveys/{survey.id}/results/responses").get_data(as_text=True)
    assert "Page 1 of 2" in html
    html = auth_client.get(f"/surveys/{survey.id}/results/responses?page=2").get_data(as_text=True)
    assert "Newer" in html and "Older" not in html


def test_responses_list_is_owner_only(auth_client):
    survey = make_published_survey(make_user("other@example.com"))
    assert auth_client.get(f"/surveys/{survey.id}/results/responses").status_code == 404


def test_response_detail_shows_every_answer(auth_client, owner):
    from datetime import date

    survey = make_published_survey(
        owner,
        [
            [
                ("short_text", "Name", {}),
                ("multiple_choice", "Pets", {"choices": ["Cat", "Dog"]}),
                ("rating", "Mood", {"settings": {"scale": 5}}),
                ("date", "Birthday", {}),
                ("long_text", "Skipped", {}),
            ]
        ],
    )
    name, pets, mood, birthday, _ = survey.questions
    response = add_response(
        survey, {name: "Ana", pets: ["Cat", "Dog"], mood: 4, birthday: date(1990, 5, 17)}
    )
    html = auth_client.get(f"/surveys/{survey.id}/results/responses/{response.id}").get_data(
        as_text=True
    )
    assert "Ana" in html
    assert "Cat, Dog" in html
    assert "4 / 5" in html
    assert "1990-05-17" in html
    assert "No answer" in html


def test_response_detail_unknown_id(auth_client, owner):
    survey = make_published_survey(owner)
    assert auth_client.get(f"/surveys/{survey.id}/results/responses/999").status_code == 404
