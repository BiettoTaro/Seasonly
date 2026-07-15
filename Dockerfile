FROM python:3.12-slim AS base

ARG UV_VERSION=0.11.21

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONPATH=/app/backend
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock README.md alembic.ini ./
RUN uv sync --locked --no-dev --no-editable

COPY backend ./backend

RUN addgroup --system seasonly && adduser --system --ingroup seasonly seasonly \
    && chown -R seasonly:seasonly /app

USER seasonly

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8001"]
