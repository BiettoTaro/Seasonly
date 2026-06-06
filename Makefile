.PHONY: build up lint

.env:
	cp .env.example .env

build: .env
	docker compose build

up: .env
	docker compose up

lint:
	./scripts/uv run basedpyright
	./scripts/uv run ruff check .
	./scripts/uv run ruff format --check .
