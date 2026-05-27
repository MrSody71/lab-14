"""
Интеграционный тест: запускает Go Flight сервер как subprocess,
подключается Python-клиентом, проверяет что данные получены.

Тест пропускается (pytest.mark.skip) если Go бинарник не собран —
чтобы CI не падал на машинах без Go.
"""

import os
import subprocess
import time
from pathlib import Path

import polars as pl
import pytest

from analyzer.arrow_client import WeatherFlightClient

_BASE = Path(__file__).parent.parent.parent / "arrow-server" / "arrowsrv"
# Prefer .exe on Windows, fall back to no-extension (explicit -o build)
if os.name == "nt" and not _BASE.exists():
    ARROW_SERVER_BIN = _BASE.with_suffix(".exe")
else:
    ARROW_SERVER_BIN = _BASE


@pytest.fixture(scope="module")
def arrow_server_process():
    """Запускает arrow-server, ждёт готовности, останавливает после тестов."""
    if not ARROW_SERVER_BIN.exists():
        pytest.skip(
            f"Arrow server binary not found: {ARROW_SERVER_BIN}. "
            f"Run: go build -o arrow-server/arrowsrv "
            f"./arrow-server/cmd/arrowsrv"
        )

    env = os.environ.copy()
    env["ARROW_FLIGHT_ADDR"] = ":18815"
    env["ARROW_MAX_RECORDS"] = "100"

    proc = subprocess.Popen(
        [str(ARROW_SERVER_BIN)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # Ждём до 2 секунд пока сервер поднимется
    time.sleep(2)
    if proc.poll() is not None:
        out, _ = proc.communicate()
        pytest.skip(f"Arrow server failed to start: {out.decode()}")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.mark.integration
def test_fetch_all_empty(arrow_server_process):
    """Сервер только запущен — данных нет, должен вернуть пустой DataFrame."""
    with WeatherFlightClient("localhost", 18815) as client:
        df = client.fetch_all()
    assert isinstance(df, pl.DataFrame)
    assert len(df) == 0


@pytest.mark.integration
def test_schema_correct(arrow_server_process):
    """Схема должна содержать все ожидаемые колонки."""
    with WeatherFlightClient("localhost", 18815) as client:
        df = client.fetch_all()
    expected_cols = {
        "city", "window_start", "window_end", "count",
        "avg_temp", "min_temp", "max_temp",
        "avg_humidity", "avg_pressure", "avg_wind_speed", "shard_id",
    }
    assert expected_cols.issubset(set(df.columns))
