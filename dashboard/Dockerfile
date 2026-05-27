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
ENTRYPOINT ["uv", "run", "streamlit", "run", \
            "src/dashboard/app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0"]
