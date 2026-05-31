FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONPATH=/app/backend

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
RUN uv pip install --system .

COPY backend ./backend

EXPOSE 8000

CMD ["fastapi", "run", "backend/app/main.py", "--host", "0.0.0.0", "--port", "8000"]
