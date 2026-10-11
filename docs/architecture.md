# Architecture

survey-builder is a single Flask application rendered on the server. htmx swaps
fragments in the editor; everything else is plain forms and links, so the app
works without JavaScript (charts aside).

## Layout

```
survey_builder/
  __init__.py        app factory, blueprints, Jinja globals, security headers
  config.py          configuration from environment variables
  extensions.py      SQLAlchemy, Flask-Migrate, Flask-Login, CSRF
  models.py          database models
  auth.py            sign up, sign in, sign out
  account.py         profile, password, account deletion
  surveys.py         dashboard, survey settings, publish/close, duplicate, templates
  editor.py          pages, questions, choices, skip rules, preview (htmx fragments)
  public.py          the respondent flow at /s/<token>
  results.py         summary, responses, text answers, CSV export
  api.py             read-only JSON API
  cli.py, seed.py    flask seed-demo, prune-incomplete, create-user, export-csv
  logging.py         request ids and access log
  formatting.py      Jinja filters (durations, line breaks, "3 hours ago")
  domain/            logic without HTTP: validation, branching, results, export...
  templates/, static/
migrations/          Alembic migrations (Flask-Migrate)
tests/               pytest suite
```

Views stay thin: they load objects, check ownership and call into `domain/`.
The domain modules are tested directly with small fakes where possible.

## Data model

```
User 1--* Survey 1--* Page 1--* Question 1--* Choice
                 |                   |
                 |                   +--* BranchRule (choice -> target page | end)
                 +--* Response 1--* Answer (question, choice | text | number | date)
```

- Question `settings` is a JSON column holding type-specific options (length
  limits, rating scale and labels, date bounds, text format, shuffle).
- A multiple choice answer is stored as one `Answer` row per picked choice.
- Timestamps are naive UTC.

## Respondent flow

1. `GET /s/<token>` shows the page stored in the session (or the first one).
2. `POST /s/<token>` validates the page (`domain/answers.py`). The `Response`
   row is created on the first valid submission, so people who only open the
   link are not counted.
3. Answers for the page replace any earlier answers to it (the respondent may
   have gone back).
4. `domain/branching.py` picks the next page from the skip rules, or ends the
   survey. Pages visited are kept in the session for the Back button.
5. Finishing sets `completed_at`. Only completed responses appear in results,
   exports and response limits.

Progress lives in the signed session cookie for seven days. The response key
is chosen when the first page is rendered, so a double-clicked Submit reuses
it instead of starting a second response. When the survey ends, answers to
pages that were not on the final path (skipped after going Back) are dropped.

## Results

`domain/results.py` loads the answers of completed responses once and groups
them per question. A `ResponseFilter` narrows everything (summary, timeline,
funnel, export, API) to a date range and optionally to respondents who picked
one choice.

## Security notes

- Every owner route goes through `get_owned_survey`, which returns 404 for other
  people's surveys; nested objects (pages, questions, responses) are checked
  against that survey.
- CSRF tokens on every form; htmx sends the token in a header.
- Respondent text is always escaped; the CSV export neutralises cells that a
  spreadsheet would treat as formulas.
- Failed sign-ins are throttled per email and address.
- Session ids include a per-user version that is bumped on password change,
  which signs out every other device.
- A Content-Security-Policy limits scripts and styles to the app's own origin;
  public survey pages may be framed, owner pages may not.
