# survey-builder

Build surveys, share a public link and see the results in one place.

Owners sign in, put together a survey from a handful of question types, publish
it and share the link. Respondents do not need an account. Results are
summarised per question with charts, and every response can be exported as CSV.

## Features

- **Question types**: short text (optionally email or number), long text, single
  choice, multiple choice, rating scales (3 to 10 points), Net Promoter Score and dates
- **Validation**: required questions, length limits, number of choices, date ranges
- **Pages and skip logic**: split a survey into pages and jump ahead (or end the
  survey) depending on an answer
- **Sharing**: a public link with an optional close date and response limit;
  respondents stay anonymous
- **Results**: per-question charts, averages, NPS, responses per day, completion
  rate, every individual response, CSV export
- **Editor**: htmx-powered, reorder and move questions, duplicate questions or
  whole surveys, preview before publishing

## Stack

| Part     | Tech                                         |
| -------- | -------------------------------------------- |
| Web app  | Python 3.12, Flask 3, Jinja templates, htmx  |
| Database | PostgreSQL (SQLite works for development)    |
| ORM      | SQLAlchemy 2, Flask-Migrate (Alembic)        |
| Charts   | Chart.js                                     |
| Tests    | pytest                                       |
| Lint     | ruff                                         |

## Running with Docker

```bash
docker compose up --build
```

Open http://localhost:4416 and sign in with the demo account:

- **Email:** `demo@example.com`
- **Password:** `demo-password`

Set `SEED_DEMO=false` to start with an empty database, and `WEB_PORT` to use
another port.

## Local development

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt

export FLASK_APP=wsgi
flask db upgrade
flask seed-demo
flask run --debug
```

Without `DATABASE_URL` the app uses a local SQLite file.

## Configuration

| Variable         | Default                     | Description                                       |
| ---------------- | --------------------------- | ------------------------------------------------- |
| `DATABASE_URL`   | `sqlite:///survey_builder.db` | SQLAlchemy URL; `postgresql://` URLs use psycopg 3 |
| `SECRET_KEY`     | `dev-secret-change-me`      | Signs sessions and CSRF tokens. Set it in production |
| `SECURE_COOKIES` | `false`                     | Mark cookies `Secure` (turn on behind HTTPS)      |
| `ALLOW_EMBEDDING`| `false`                     | `SameSite=None; Secure` cookies so surveys work inside iframes on other sites (HTTPS only) |
| `SEED_DEMO`      | `false` (`true` in compose) | Create the demo account on container start        |
| `WEB_PORT`       | `4416`                      | Host port used by docker compose                  |
| `WEB_CONCURRENCY`| `2`                         | Gunicorn workers in the container                 |
| `LOG_LEVEL`      | `info`                      | Log level; every request is logged with its id    |

## Embedding a survey

Public survey pages may be framed. Add `?embed=1` to the share link to hide the
footer and use a transparent background:

```html
<iframe src="https://surveys.example.com/s/TOKEN?embed=1" width="100%" height="700"></iframe>
```

When the iframe is on another domain, browsers only send the session cookie if
it is `SameSite=None; Secure`. Set `ALLOW_EMBEDDING=true` and serve the app over
HTTPS, otherwise respondents cannot get past the first page.

## API

A read-only JSON API is described in [docs/api.md](docs/api.md). How the code is
organised is described in [docs/architecture.md](docs/architecture.md), and running
it in production in [docs/deployment.md](docs/deployment.md).

## Tests

```bash
pytest
ruff check . && ruff format --check .
```

Optional: `pip install pre-commit && pre-commit install` runs ruff on every commit.

The `Makefile` wraps the usual commands: `make install`, `make dev`, `make check`,
`make format`, `make up`.

## License

MIT
