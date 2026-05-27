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
