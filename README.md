# Seasonly

Seasonly is a final-year software engineering project for an iOS app backed by a FastAPI monolith
and PostgreSQL database.

The app focuses on seasonal produce in Europe, recipe data, authentication, validation and a
consent-aware TF-IDF recommendation feed.

## Repository Layout

```text
.
├── backend/              # FastAPI application
├── ios/                  # Swift/iOS app workspace placeholder
├── docs/                 # Project notes and research
├── datasets/             # Dataset staging area, excluding generated extracts
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
./scripts/uv run uvicorn app.main:app --reload --app-dir backend
```

Run linting and formatting checks:

```bash
./scripts/uv run ruff check .
./scripts/uv run ruff format --check .
```

Run tests:

```bash
./scripts/uv run python -m pytest
```

If your shell has a global `UV_PYTHON` override for another project, use `./scripts/uv ...` in this repository. It keeps Seasonly on Python 3.12, uses a repo-local uv cache, and sets `PYTHONPATH=backend` without changing your global uv setup.

If the repository is moved, recreate `.venv` with `uv venv --clear` followed by
`./scripts/uv sync --all-extras --dev`; virtual-environment command entry points contain absolute
paths. The module-form test and type-check commands above also avoid stale entry-point shebangs.

## Docker Development

Copy the environment template:

```bash
cp .env.example .env
```

Start PostgreSQL and the API:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8001`.

Compose binds the API and PostgreSQL to `127.0.0.1` by default. Override `API_BIND_HOST` or
`POSTGRES_BIND_HOST` only when the service must be reachable from another host and the surrounding
network is appropriately restricted.

Production settings are fail-closed: use `APP_ENV=production`, disable debug mode, enable HTTPS,
set explicit trusted hosts, provide a unique 32+ character `AUTH_SECRET_KEY`, replace development
database credentials, and configure SMTP password-reset delivery. Release iOS builds likewise
require an HTTPS `SEASONLY_API_BASE_URL` build setting.

The reviewed recommendation policy defaults to `RECOMMENDATION_RANKING_MODE=seasonal_tfidf_v1`.
Operators can select `seasonal_only_v1` for an immediate safety-preserving rollback; unknown values
stop application startup. The procedure and privacy-safe measurements are documented in
`docs/recommendation-operations.md`.

Current ML development remains synthetic-only. The planned brief private sessions are for
formative usability and safety presentation, not model training or recommendation-effectiveness
claims; see `docs/private-pilot-and-synthetic-ml.md`.

The fully executed `notebooks/seasonly_ml_exploration.ipynb` presents the checksummed synthetic
data, preprocessing controls, model formulas, visual comparisons and production model decision.
It reads immutable evidence rather than retraining models. Start the optional notebook environment
from the repository root with:

```bash
./scripts/uv run --group notebook jupyter lab
```

Authenticated users can download a versioned JSON copy of their stored Seasonly data or permanently
delete their account from the iOS profile screen. Both actions require current-password
reconfirmation, and deletion also requires an exact typed confirmation. Scope and limitations are
documented in `docs/privacy-controls.md`.

Apply database migrations before using persistence-backed endpoints. Docker Compose runs this as a
separate one-shot `migrate` service before starting the API:

```bash
./scripts/uv run alembic upgrade head
```

## Planned Data Work

- Seasonal produce datasets for Europe.
- Recipe datasets relevant to European ingredients and cuisine.
- Data architecture starts with modular `data_key`, `data_source`, `data_target`, `contracts`, `enums`, and `registry` modules in `backend/app/data/`.
- Dataset provenance, licensing, and refresh notes should be documented in `docs/data-sources.md`.

## Planned Features

- Secure sign-up and login.
- Pydantic request/response models.
- PostgreSQL persistence.
- Consent-aware seasonal TF-IDF recommendation feed.
- Optional Cloudflare Tunnel support for device testing.
