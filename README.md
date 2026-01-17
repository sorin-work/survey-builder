# survey-builder

Build surveys, share a public link and see the results in one place.

Owners sign in, put together a survey from a handful of question types, publish
it and share the link. Respondents do not need an account. Results are
summarised per question with charts, and every response can be exported as CSV.

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

## Tests

```bash
pytest
ruff check . && ruff format --check .
```

## License

MIT
