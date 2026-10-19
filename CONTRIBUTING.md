# Contributing

Thanks for taking the time to improve survey-builder.

## Setup

```bash
python3.12 -m venv .venv && . .venv/bin/activate
make install
make db seed
make dev
```

## Before opening a pull request

- `make check` runs ruff (lint and format check) and the test suite.
- Add a test for every bug fix that fails without the fix.
- Keep views thin; put logic in `survey_builder/domain/` and test it there.
- Schema changes need a migration: `FLASK_APP=wsgi flask db migrate -m "what changed"`,
  then review the generated file. Migrations should only add things, so the
  previous release keeps working against the new schema.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/): `feat(editor): ...`,
`fix(public): ...`, `docs: ...`, `test: ...`, `chore(deps): ...`. Describe the
change from the user's point of view.
