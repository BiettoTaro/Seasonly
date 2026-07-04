FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONPATH=/app/backend

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md alembic.ini ./
RUN uv pip install --system .

COPY backend ./backend

EXPOSE 8001

CMD ["sh", "-c", "alembic -c /app/alembic.ini upgrade head && exec uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8001"]
