# Seasonly

Seasonly is a final-year software engineering project for an iOS app backed by a FastAPI monolith and PostgreSQL database.

The app will focus on seasonal produce in Europe, recipe data, authentication, validation, and later recommendation features using machine learning.

## Repository Layout

```text
.
├── backend/              # FastAPI application
├── ios/                  # Swift/iOS app workspace placeholder
├── docs/                 # Project notes and research
├── data/                 # Dataset staging area, excluded except README files
├── infra/                # Local/dev infrastructure config
├── .codex/               # Project-specific assistant instructions and skills
├── docker-compose.yml    # API + PostgreSQL development stack
├── Dockerfile            # Backend container image
├── pyproject.toml        # Python project, uv, Ruff, pytest config
└── .env.example          # Environment variable template
```

## Backend Setup

Prerequisites:

- Python 3.12
- Docker Desktop
- uv

This project is pinned to Python 3.12 through `.python-version`, `pyproject.toml`, and the local `./scripts/uv` wrapper. The wrapper also keeps uv's cache local to this repository.

Create a virtual environment and install dependencies:

```bash
uv venv
./scripts/uv sync --all-extras --dev
```

Run the API locally:

```bash
./scripts/uv run fastapi dev backend/app/main.py
```

Run linting and formatting checks:

```bash
./scripts/uv run ruff check .
./scripts/uv run ruff format --check .
```

Run tests:

```bash
./scripts/uv run pytest
```

If your shell has a global `UV_PYTHON` override for another project, use `./scripts/uv ...` in this repository. It keeps Seasonly on Python 3.12, uses a repo-local uv cache, and sets `PYTHONPATH=backend` without changing your global uv setup.

## Docker Development

Copy the environment template:

```bash
cp .env.example .env
```

Start PostgreSQL and the API:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## Planned Data Work

- Seasonal produce datasets for Europe.
- Recipe datasets relevant to European ingredients and cuisine.
- Data architecture starts with modular `data_key`, `enums`, `data_target`, and `data/schemas` packages in `backend/app/data/`.
- Dataset provenance, licensing, and refresh notes should be documented in `docs/data-sources.md`.

## Planned Features

- Secure sign-up and login.
- Pydantic request/response models.
- PostgreSQL persistence.
- Recommendation system with machine learning.
- Optional Cloudflare Tunnel support for device testing.
