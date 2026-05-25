# Промт 0.5 — Python-проекты

Прочитай CLAUDE.md.

Создай три Python-проекта (py-analyzer, py-asyncio-collector, dashboard)
с управлением через uv и src-layout. Зависимости перечисли БЕЗ версий —
закрепим в этапе 5 командой uv lock.

ФАЙЛЫ:

=== py-analyzer/pyproject.toml ===
[project]
name = "weather-analyzer"
version = "0.0.0"
description = "Polars + DuckDB analyzer for weather pipeline"
requires-python = ">=3.11"
dependencies = [
    "polars",
    "duckdb",
    "pyarrow",
    "kafka-python",
    "nats-py",
    "plotly",
    "matplotlib",
    "altair",
    "pydantic",
    "typer",
    "rich",
]

[dependency-groups]
dev = [
    "pytest",
    "pytest-asyncio",
    "pytest-benchmark",
    "ruff",
    "mypy",
    "hypothesis",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/analyzer"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]

[tool.pytest.ini_options]
testpaths = ["tests"]

=== py-analyzer/src/analyzer/__init__.py ===
"""Weather pipeline analyzer."""
__version__ = "0.0.0"

=== py-analyzer/tests/test_smoke.py ===
from analyzer import __version__

def test_version():
    assert __version__ == "0.0.0"

=== py-asyncio-collector/pyproject.toml ===
Аналогично py-analyzer, но:
  name = "weather-asyncio-collector"
  description = "Reference asyncio collector for benchmarking vs Go"
  dependencies = ["aiohttp", "httpx", "rich", "typer", "pydantic"]
  packages = ["src/collector"]

=== py-asyncio-collector/src/collector/__init__.py ===
"""Reference asyncio collector."""
__version__ = "0.0.0"

=== py-asyncio-collector/tests/test_smoke.py ===
from collector import __version__

def test_version():
    assert __version__ == "0.0.0"

=== dashboard/pyproject.toml ===
Аналогично, но:
  name = "weather-dashboard"
  description = "Streamlit dashboard for weather pipeline"
  dependencies = ["streamlit", "plotly", "pyarrow", "polars",
                  "kafka-python", "nats-py", "pydantic"]
  packages = ["src/dashboard"]

=== dashboard/src/dashboard/__init__.py ===
"""Weather pipeline dashboard."""
__version__ = "0.0.0"

=== dashboard/tests/test_smoke.py ===
from dashboard import __version__

def test_version():
    assert __version__ == "0.0.0"

КАТАЛОГИ (создай tests/ где их нет, src/<pkg>/ тоже):
- py-asyncio-collector/src/collector/
- dashboard/src/dashboard/
- везде создай __init__.py в src/<pkg>/ и в tests/

Удали .gitkeep в любых каталогах, где теперь есть код.

ПРОВЕРКА (выполни в каждом py-проекте, покажи вывод):
  cd py-analyzer && uv sync && uv run pytest && uv run ruff check && cd ..
  cd py-asyncio-collector && uv sync && uv run pytest && uv run ruff check && cd ..
  cd dashboard && uv sync && uv run pytest && uv run ruff check && cd ..

Все три pytest должны показать "1 passed". Если uv не установлен —
скажи мне ОДНОЙ строкой "uv not installed" и остановись, не пытайся
устанавливать его сам.

prompts/00-5-python-projects.md — этот промт целиком.

В конце: git status.
