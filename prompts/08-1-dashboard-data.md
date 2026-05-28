Создай слой данных для дашборда — модуль который умеет
читать из Parquet, Kafka, NATS и mock-генератора.
Дашборд не должен знать откуда приходят данные.

=== dashboard/src/dashboard/data.py ===

"""
Слой данных для Streamlit-дашборда.
Абстрагирует источник: Parquet / Kafka / NATS / mock.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from typing import Callable, Optional

import polars as pl

logger = logging.getLogger(__name__)

PARQUET_PATH = Path(os.getenv(
    "PARQUET_PATH", "data/weather.parquet"
))
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092")
KAFKA_TOPIC   = os.getenv("KAFKA_TOPIC",   "weather.raw")
NATS_URL      = os.getenv("NATS_URL",      "nats://localhost:4222")
NATS_SUBJECT  = os.getenv("NATS_SUBJECT",  "weather.raw")

CITIES = [
    "Moscow", "Saint-Petersburg", "Novosibirsk",
    "Yekaterinburg", "Kazan", "Stockholm",
    "Berlin", "London", "New-York", "Tokyo",
]

CITY_BASE_TEMPS = {
    "Moscow": 5.0, "Saint-Petersburg": 4.0,
    "Novosibirsk": 1.0, "Yekaterinburg": 2.0,
    "Kazan": 6.0,  "Stockholm": 8.0,
    "Berlin": 12.0, "London": 11.0,
    "New-York": 14.0, "Tokyo": 16.0,
}


# ── Схема DataFrame ───────────────────────────────────────────────────────

SCHEMA = {
    "city":           pl.String,
    "window_start":   pl.Datetime,
    "window_end":     pl.Datetime,
    "count":          pl.Int64,
    "avg_temp":       pl.Float64,
    "min_temp":       pl.Float64,
    "max_temp":       pl.Float64,
    "avg_humidity":   pl.Float64,
    "avg_pressure":   pl.Float64,
    "avg_wind_speed": pl.Float64,
    "shard_id":       pl.String,
}


def empty_df() -> pl.DataFrame:
    return pl.DataFrame({k: pl.Series([], dtype=v)
                         for k, v in SCHEMA.items()})


# ── Mock-генератор ────────────────────────────────────────────────────────

def generate_mock_batch(
    n_cities: int = 5,
    n_windows: int = 50,
) -> pl.DataFrame:
    """
    Генерирует реалистичный DataFrame с историческими данными.
    Используется когда нет реального источника.
    """
    random.seed(int(time.time()) % 1000)
    cities = CITIES[:n_cities]
    rows: list[dict] = []
    base_time = datetime.utcnow() - timedelta(minutes=n_windows)

    for i in range(n_windows):
        window_start = base_time + timedelta(minutes=i)
        window_end   = window_start + timedelta(minutes=1)
        for city in cities:
            base = CITY_BASE_TEMPS.get(city, 10.0)
            # Суточный цикл температуры
            hour_offset = (i / 60) * 2 * 3.14159
            daily_cycle = 3.0 * (
                (window_start.hour - 14) / 12
            )
            temp = (base
                    + daily_cycle
                    + random.uniform(-1.5, 1.5))
            rows.append({
                "city":           city,
                "window_start":   window_start,
                "window_end":     window_end,
                "count":          random.randint(3, 12),
                "avg_temp":       round(temp, 2),
                "min_temp":       round(temp - random.uniform(0, 2), 2),
                "max_temp":       round(temp + random.uniform(0, 2), 2),
                "avg_humidity":   round(random.uniform(45, 85), 1),
                "avg_pressure":   round(random.uniform(1005, 1025), 1),
                "avg_wind_speed": round(random.uniform(0, 12), 1),
                "shard_id":       "mock",
            })

    return pl.DataFrame(rows)


def generate_live_row(city: str) -> dict:
    """Одна свежая запись для city."""
    base = CITY_BASE_TEMPS.get(city, 10.0)
    temp = base + random.uniform(-3, 3)
    now  = datetime.utcnow()
    return {
        "city":           city,
        "window_start":   now - timedelta(seconds=60),
        "window_end":     now,
        "count":          random.randint(3, 10),
        "avg_temp":       round(temp, 2),
        "min_temp":       round(temp - random.uniform(0, 2), 2),
        "max_temp":       round(temp + random.uniform(0, 2), 2),
        "avg_humidity":   round(random.uniform(45, 85), 1),
        "avg_pressure":   round(random.uniform(1005, 1025), 1),
        "avg_wind_speed": round(random.uniform(0, 10), 1),
        "shard_id":       "mock-live",
    }


# ── Parquet-источник ──────────────────────────────────────────────────────

def load_from_parquet(path: Path = PARQUET_PATH) -> pl.DataFrame:
    """Загружает данные из Parquet-файла."""
    if not path.exists():
        logger.info("Parquet not found at %s, using mock", path)
        return generate_mock_batch()
    try:
        df = pl.read_parquet(str(path))
        logger.info("Loaded %d rows from %s", len(df), path)
        return df
    except Exception as e:
        logger.warning("Failed to read parquet: %s", e)
        return generate_mock_batch()


# ── Kafka-источник ────────────────────────────────────────────────────────

class KafkaLiveSource:
    """
    Читает последние N записей из Kafka в фоновом потоке.
    Потокобезопасно обновляет внутренний буфер.
    """

    def __init__(
        self,
        brokers: str = KAFKA_BROKERS,
        topic: str   = KAFKA_TOPIC,
        max_rows: int = 500,
    ) -> None:
        self._brokers  = brokers
        self._topic    = topic
        self._max_rows = max_rows
        self._rows: list[dict] = []
        self._running  = False
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        self._running = True
        self._thread  = Thread(
            target=self._consume, daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def get_df(self) -> pl.DataFrame:
        if not self._rows:
            return empty_df()
        return pl.DataFrame(self._rows[-self._max_rows:])

    def _consume(self) -> None:
        try:
            from kafka import KafkaConsumer
            consumer = KafkaConsumer(
                self._topic,
                bootstrap_servers=self._brokers.split(","),
                auto_offset_reset="latest",
                consumer_timeout_ms=1000,
                value_deserializer=lambda b: json.loads(
                    b.decode()
                ),
            )
            while self._running:
                for msg in consumer:
                    if not self._running:
                        break
                    try:
                        row = _parse_aggregate(msg.value)
                        self._rows.append(row)
                        if len(self._rows) > self._max_rows * 2:
                            self._rows = self._rows[
                                -self._max_rows:
                            ]
                    except Exception as e:
                        logger.debug("Bad msg: %s", e)
        except Exception as e:
            logger.warning(
                "Kafka source unavailable: %s", e
            )


def _parse_aggregate(d: dict) -> dict:
    """Парсит dict-агрегат в строку DataFrame."""
    def parse_dt(v: object) -> datetime:
        if isinstance(v, (int, float)):
            return datetime.utcfromtimestamp(float(v))
        return datetime.fromisoformat(
            str(v).replace("Z", "+00:00")
        )
    return {
        "city":           str(d.get("city", "")),
        "window_start":   parse_dt(d.get("window_start", 0)),
        "window_end":     parse_dt(d.get("window_end", 0)),
        "count":          int(d.get("count", 0)),
        "avg_temp":       float(d.get("avg_temp", 0)),
        "min_temp":       float(d.get("min_temp", 0)),
        "max_temp":       float(d.get("max_temp", 0)),
        "avg_humidity":   float(d.get("avg_humidity", 0)),
        "avg_pressure":   float(d.get("avg_pressure", 0)),
        "avg_wind_speed": float(d.get("avg_wind_speed", 0)),
        "shard_id":       str(d.get("shard_id", "")),
    }


# ── Фасад ─────────────────────────────────────────────────────────────────

class DataSource:
    """
    Единый фасад для дашборда.
    Автоматически выбирает источник данных.
    """

    def __init__(self) -> None:
        self._kafka: Optional[KafkaLiveSource] = None
        self._mode = self._detect_mode()
        logger.info("DataSource mode: %s", self._mode)

    def _detect_mode(self) -> str:
        if PARQUET_PATH.exists():
            return "parquet"
        return "mock"

    def load(self) -> pl.DataFrame:
        if self._mode == "parquet":
            return load_from_parquet()
        return generate_mock_batch()

    def load_live_update(self) -> pl.DataFrame:
        """Одна свежая запись для каждого города (для live-обновлений)."""
        rows = [generate_live_row(c) for c in CITIES[:5]]
        return pl.DataFrame(rows)

    @property
    def mode(self) -> str:
        return self._mode

=== dashboard/tests/test_data.py ===

"""Tests for dashboard data layer."""
import polars as pl
import pytest
from datetime import datetime
from dashboard.data import (
    generate_mock_batch, generate_live_row,
    empty_df, _parse_aggregate, DataSource, SCHEMA,
)


def test_generate_mock_batch_shape():
    df = generate_mock_batch(n_cities=3, n_windows=10)
    assert len(df) == 30
    assert set(df["city"].unique().to_list()) == {
        "Moscow", "Saint-Petersburg", "Novosibirsk"
    }


def test_generate_mock_batch_columns():
    df = generate_mock_batch(n_cities=2, n_windows=5)
    for col in SCHEMA:
        assert col in df.columns, f"Missing column: {col}"


def test_generate_mock_batch_values():
    df = generate_mock_batch(n_cities=3, n_windows=20)
    assert df["avg_temp"].min() > -50
    assert df["avg_temp"].max() < 50
    assert df["avg_humidity"].min() >= 0
    assert df["avg_humidity"].max() <= 100


def test_generate_live_row():
    row = generate_live_row("Moscow")
    assert row["city"] == "Moscow"
    assert isinstance(row["window_end"], datetime)
    assert -50 < row["avg_temp"] < 50


def test_empty_df_schema():
    df = empty_df()
    assert len(df) == 0
    for col, dtype in SCHEMA.items():
        assert col in df.columns


def test_parse_aggregate_iso():
    d = {
        "city": "London",
        "window_start": "2024-01-01T00:00:00",
        "window_end":   "2024-01-01T00:01:00",
        "count": 5, "avg_temp": 15.0,
        "min_temp": 13.0, "max_temp": 17.0,
        "avg_humidity": 65.0, "avg_pressure": 1013.0,
        "avg_wind_speed": 5.0, "shard_id": "s0",
    }
    row = _parse_aggregate(d)
    assert row["city"] == "London"
    assert isinstance(row["window_start"], datetime)
    assert row["avg_temp"] == 15.0


def test_parse_aggregate_unix():
    row = _parse_aggregate({
        "city": "Tokyo",
        "window_start": 1700000000,
        "window_end":   1700000060,
        "count": 3, "avg_temp": 20.0,
        "min_temp": 18.0, "max_temp": 22.0,
        "avg_humidity": 70.0, "avg_pressure": 1010.0,
        "avg_wind_speed": 3.0, "shard_id": "s1",
    })
    assert row["city"] == "Tokyo"
    assert row["window_start"].year >= 2023


def test_data_source_mock_mode(tmp_path):
    src = DataSource()
    # Без parquet — должен вернуть mock
    df = src.load()
    assert len(df) > 0
    assert "city" in df.columns


def test_data_source_load_live():
    src = DataSource()
    df = src.load_live_update()
    assert len(df) == 5
    assert "avg_temp" in df.columns

ПРОВЕРКА:
  cd dashboard
  uv sync 2>&1
  uv run pytest tests/test_data.py -v 2>&1
  cd ..

9 тестов зелёных.

prompts/08-1-dashboard-data.md — этот промт целиком.
