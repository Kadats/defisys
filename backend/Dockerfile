# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.3

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock ./

FROM base AS builder

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main --no-root

# Ensure uvicorn has websocket protocol support at runtime.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir "websockets>=10.4,<16"

COPY backend ./backend

FROM base AS test

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --with dev --no-root

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir "websockets>=10.4,<16"

COPY backend ./backend

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app/backend /app/backend

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.src.api:app", "--host", "0.0.0.0", "--port", "8000"]
