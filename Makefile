.PHONY: install dev test lint format check db seed up down

install:
	pip install -r requirements-dev.txt

dev:
	FLASK_APP=wsgi flask run --debug

test:
	pytest -q

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

check: lint test

db:
	FLASK_APP=wsgi flask db upgrade

seed:
	FLASK_APP=wsgi flask seed-demo

up:
	docker compose up -d --build

down:
	docker compose down
