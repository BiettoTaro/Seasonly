.PHONY: build up lint test

.env:
	cp .env.example .env
	chmod 600 .env

build: .env
	docker compose build

up: .env
	docker compose up

lint:
	./scripts/uv run python -m basedpyright
	./scripts/uv run ruff check .
	./scripts/uv run ruff format --check .

test:
	./scripts/uv run python -m pytest
