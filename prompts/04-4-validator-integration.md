Прочитай CLAUDE.md.

Подключи Rust-валидатор в основной pipeline py-analyzer.
Нужен один модуль, который принимает DataFrame Polars,
прогоняет каждую строку через Rust-валидатор и возвращает
очищенный DataFrame + отчёт.

=== py-analyzer/src/analyzer/validator.py ===

"""
Интеграция Rust-валидатора в Polars pipeline.
Принимает DataFrame с погодными данными, возвращает
отфильтрованный DataFrame и отчёт о качестве данных.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import polars as pl

logger = logging.getLogger(__name__)

try:
    import weather_validator as _wv
    _RUST_AVAILABLE = True
except ImportError:
    _wv = None  # type: ignore[assignment]
    _RUST_AVAILABLE = False
    logger.warning(
        "Rust weather_validator not available. "
        "Using Python fallback validation."
    )


@dataclass
class ValidationReport:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    errors_by_field: dict[str, int] = field(default_factory=dict)
    duration_ms: float = 0.0
    backend: str = "unknown"

    @property
    def valid_pct(self) -> float:
        return (self.valid / self.total * 100) if self.total > 0 else 0.0

    def __str__(self) -> str:
        return (
            f"ValidationReport(total={self.total}, "
            f"valid={self.valid} ({self.valid_pct:.1f}%), "
            f"invalid={self.invalid}, "
            f"backend={self.backend}, "
            f"duration={self.duration_ms:.1f}ms)"
        )


def validate_dataframe(
    df: pl.DataFrame,
    now_unix: Optional[int] = None,
) -> tuple[pl.DataFrame, ValidationReport]:
    """
    Валидирует DataFrame с погодными показаниями.

    Ожидаемые колонки: city, temperature, humidity, pressure,
                       wind_speed, collected_at (datetime или unix int).

    Returns:
        (clean_df, report) — отфильтрованный DataFrame и отчёт.
    """
    if now_unix is None:
        now_unix = int(time.time())

    report = ValidationReport(total=len(df))
    if len(df) == 0:
        report.backend = "rust" if _RUST_AVAILABLE else "python"
        return df, report

    t0 = time.perf_counter()

    if _RUST_AVAILABLE:
        clean_df, report = _validate_rust(df, now_unix, report)
    else:
        clean_df, report = _validate_python(df, now_unix, report)

    report.duration_ms = (time.perf_counter() - t0) * 1000
    logger.info("Validation complete: %s", report)
    return clean_df, report


def _validate_rust(
    df: pl.DataFrame,
    now_unix: int,
    report: ValidationReport,
) -> tuple[pl.DataFrame, ValidationReport]:
    """Валидация через Rust-модуль."""
    report.backend = "rust"

    # Преобразуем datetime → unix int если нужно
    ts_col = _get_timestamp_unix(df)

    records = [
        {
            "city":           row[0],
            "temperature":    float(row[1]),
            "humidity":       int(row[2]),
            "pressure":       int(row[3]),
            "wind_speed":     float(row[4]),
            "timestamp_unix": int(row[5]),
        }
        for row in df.select([
            "city", "temperature", "humidity",
            "pressure", "wind_speed", ts_col,
        ]).iter_rows()
    ]

    result = _wv.validate_batch_records(records, now_unix=now_unix)
    report.valid = result["valid"]
    report.invalid = result["invalid"]

    # Считаем ошибки по полям
    for err in result["errors"]:
        f = err["field"]
        report.errors_by_field[f] = report.errors_by_field.get(f, 0) + 1

    # Фильтруем: оставляем только валидные строки
    invalid_indices = {e["index"] for e in result["errors"]}
    if invalid_indices:
        mask = pl.Series(
            [i not in invalid_indices for i in range(len(df))]
        )
        clean_df = df.filter(mask)
    else:
        clean_df = df

    return clean_df, report


def _validate_python(
    df: pl.DataFrame,
    now_unix: int,
    report: ValidationReport,
) -> tuple[pl.DataFrame, ValidationReport]:
    """Fallback Python-валидация если Rust недоступен."""
    report.backend = "python"
    valid_mask = (
        pl.col("temperature").is_between(-80, 60)
        & pl.col("humidity").is_between(0, 100)
        & pl.col("pressure").is_between(870, 1085)
        & pl.col("wind_speed").is_between(0, 120)
        & pl.col("city").str.len_chars().gt(0)
    )
    clean_df = df.filter(valid_mask)
    report.valid = len(clean_df)
    report.invalid = len(df) - len(clean_df)
    return clean_df, report


def _get_timestamp_unix(df: pl.DataFrame) -> str:
    """Возвращает имя колонки с unix timestamp.
    Если колонка collected_at datetime — создаёт вспомогательную."""
    if "timestamp_unix" in df.columns:
        return "timestamp_unix"
    if "collected_at" in df.columns:
        dtype = df["collected_at"].dtype
        if dtype == pl.Datetime:
            # Полars epoch_seconds
            return "collected_at"
    # Запасной вариант — текущее время
    return "collected_at"

=== py-analyzer/tests/test_validator_integration.py ===

"""Tests for validator.py — Polars DataFrame validation pipeline."""
import time
import polars as pl
import pytest
from analyzer.validator import validate_dataframe, ValidationReport

NOW = int(time.time())


def make_df(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def valid_row(**kwargs) -> dict:
    base = {
        "city": "Moscow",
        "temperature": 15.0,
        "humidity": 65,
        "pressure": 1013,
        "wind_speed": 5.0,
        "collected_at": NOW - 10,
    }
    base.update(kwargs)
    return base


def test_all_valid():
    df = make_df([valid_row(), valid_row(city="London")])
    clean, report = validate_dataframe(df, now_unix=NOW)
    assert report.total == 2
    assert report.valid == 2
    assert report.invalid == 0
    assert len(clean) == 2


def test_one_invalid_filtered_out():
    df = make_df([
        valid_row(),
        valid_row(temperature=999.0),
        valid_row(city="Berlin"),
    ])
    clean, report = validate_dataframe(df, now_unix=NOW)
    assert report.total == 3
    assert report.invalid == 1
    assert len(clean) == 2


def test_empty_dataframe():
    df = pl.DataFrame({
        "city": [], "temperature": [], "humidity": [],
        "pressure": [], "wind_speed": [], "collected_at": [],
    })
    clean, report = validate_dataframe(df, now_unix=NOW)
    assert report.total == 0
    assert len(clean) == 0


def test_report_str():
    df = make_df([valid_row()])
    _, report = validate_dataframe(df, now_unix=NOW)
    s = str(report)
    assert "total=1" in s
    assert "backend=" in s


def test_valid_pct_full():
    df = make_df([valid_row(), valid_row()])
    _, report = validate_dataframe(df, now_unix=NOW)
    assert report.valid_pct == 100.0

ПРОВЕРКА:
  cd py-analyzer
  uv run pytest tests/test_validator_integration.py -v 2>&1
  uv run pytest tests/ -v --ignore=tests/test_arrow_integration.py 2>&1
  cd ..

Все тесты зелёные.

prompts/04-4-validator-integration.md — этот промт целиком.
