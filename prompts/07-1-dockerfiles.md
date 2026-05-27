Создай Dockerfile для каждого сервиса который будет
деплоиться в Kubernetes. Образы должны быть минимальными
и собираться без ошибок.

=== go-collector/Dockerfile ===

# Multi-stage: сборка в golang, запуск в distroless
FROM golang:1.22-alpine AS builder
WORKDIR /app

# Зависимости отдельным слоем для кеша
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-w -s" \
    -o collector \
    ./cmd/collector

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/collector .
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/app/collector"]

=== arrow-server/Dockerfile ===

FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-w -s" \
    -o arrowsrv \
    ./cmd/arrowsrv

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/arrowsrv .
EXPOSE 8815
USER nonroot:nonroot
ENTRYPOINT ["/app/arrowsrv"]

=== mock-owm/Dockerfile ===

Уже существует — проверь что он есть и корректен.
Если есть — не трогай.

=== py-analyzer/Dockerfile ===

FROM python:3.11-slim AS base
WORKDIR /app

# uv для быстрой установки зависимостей
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Зависимости
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Исходники
COPY src/ ./src/
RUN uv sync --no-dev

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

ENTRYPOINT ["uv", "run", "python", "-m", "analyzer.pipeline"]
CMD ["--mock"]

=== dashboard/Dockerfile ===

FROM python:3.11-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project
COPY src/ ./src/
RUN uv sync --no-dev

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

EXPOSE 8501
ENTRYPOINT ["uv", "run", "streamlit", "run",
            "src/dashboard/app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0"]

ВАЖНО: dashboard/src/dashboard/app.py ещё не существует —
создай заглушку:

=== dashboard/src/dashboard/app.py (заглушка) ===

import streamlit as st
st.title("Weather Pipeline Dashboard")
st.info("Dashboard will be implemented in stage 8.")

=== .dockerignore в корне ===

.git
.github
**/.venv
**/node_modules
**/target
**/__pycache__
**/*.pyc
**/.pytest_cache
**/.mypy_cache
**/bench/results
**/data
docs/screenshots

ПРОВЕРКА:

1. Собери образы (не запускай):
  docker build -t weather-collector:test ./go-collector 2>&1 \
    && echo "collector OK"
  docker build -t weather-arrow:test ./arrow-server 2>&1 \
    && echo "arrow-server OK"
  docker build -t weather-mock:test ./mock-owm 2>&1 \
    && echo "mock-owm OK"

2. Проверь размер образов:
  docker images | grep weather

3. go-collector и arrow-server должны быть < 30MB
   (distroless + static binary).

Если сборка падает — исправь Dockerfile и повтори.
Покажи мне вывод docker images.

prompts/07-1-dockerfiles.md — этот промт целиком.
