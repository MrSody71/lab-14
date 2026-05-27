Реализуй Polars-трансформации и сохранение в Parquet.
Этот модуль принимает список WindowAggregate,
конвертирует в DataFrame, чистит и сохраняет.

=== py-analyzer/src/analyzer/transforms.py ===

"""
Polars-трансформации для weather pipeline.
Принимает list[WindowAggregate] → DataFrame → Parquet.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import polars as pl

from analyzer.consumers import WindowAggregate
from analyzer.validator import validate_dataframe

logger = logging.getLogger(__name__)


# ── Конвертация в DataFrame ───────────────────────────────────────────────

def aggregates_to_df(records: list[WindowAggregate]) -> pl.DataFrame:
    """Конвертирует список WindowAggregate в Polars DataFrame."""
    if not records:
        return _empty_agg_df()

    return pl.DataFrame({
        "city":           [r.city for r in records],
        "window_start":   [r.window_start for r in records],
        "window_end":     [r.window_end for r in records],
        "count":          [r.count for r in records],
        "avg_temp":       [r.avg_temp for r in records],
        "min_temp":       [r.min_temp for r in records],
        "max_temp":       [r.max_temp for r in records],
        "avg_humidity":   [r.avg_humidity for r in records],
        "avg_pressure":   [r.avg_pressure for r in records],
        "avg_wind_speed": [r.avg_wind_speed for r in records],
        "shard_id":       [r.shard_id for r in records],
    })


def _empty_agg_df() -> pl.DataFrame:
    return pl.DataFrame({
        "city":           pl.Series([], dtype=pl.String),
        "window_start":   pl.Series([], dtype=pl.Datetime),
        "window_end":     pl.Series([], dtype=pl.Datetime),
        "count":          pl.Series([], dtype=pl.Int64),
        "avg_temp":       pl.Series([], dtype=pl.Float64),
        "min_temp":       pl.Series([], dtype=pl.Float64),
        "max_temp":       pl.Series([], dtype=pl.Float64),
        "avg_humidity":   pl.Series([], dtype=pl.Float64),
        "avg_pressure":   pl.Series([], dtype=pl.Float64),
        "avg_wind_speed": pl.Series([], dtype=pl.Float64),
        "shard_id":       pl.Series([], dtype=pl.String),
    })


# ── Трансформации ─────────────────────────────────────────────────────────

def enrich(df: pl.DataFrame) -> pl.DataFrame:
    """
    Обогащает DataFrame вычисляемыми полями:
    - temp_range: разброс температуры в окне
    - window_duration_sec: длина окна в секундах
    - comfort_index: упрощённый индекс комфорта [0-100]
    """
    if len(df) == 0:
        return df

    return df.with_columns([
        # Разброс температуры
        (pl.col("max_temp") - pl.col("min_temp"))
            .round(2)
            .alias("temp_range"),

        # Длина окна в секундах
        (
            pl.col("window_end").cast(pl.Int64) -
            pl.col("window_start").cast(pl.Int64)
        ).alias("window_duration_sec"),

        # Упрощённый индекс комфорта:
        # 100 = идеально (18°C, 50% влажность, 0 ветер)
        # штраф за отклонение от идеала
        (
            (100
             - (pl.col("avg_temp") - 18.0).abs() * 2
             - (pl.col("avg_humidity") - 50.0).abs() * 0.3
             - pl.col("avg_wind_speed") * 1.5
            ).clip(0, 100).round(1)
        ).alias("comfort_index"),
    ])


def city_summary(df: pl.DataFrame) -> pl.DataFrame:
    """
    Агрегирует по городу за всё время:
    среднее, мин, макс температуры, кол-во окон.
    """
    if len(df) == 0:
        return pl.DataFrame()

    return (
        df.group_by("city")
        .agg([
            pl.col("avg_temp").mean().round(2).alias("overall_avg_temp"),
            pl.col("min_temp").min().alias("overall_min_temp"),
            pl.col("max_temp").max().alias("overall_max_temp"),
            pl.col("avg_humidity").mean().round(1).alias("overall_avg_humidity"),
            pl.col("avg_pressure").mean().round(1).alias("overall_avg_pressure"),
            pl.col("avg_wind_speed").mean().round(2).alias("overall_avg_wind"),
            pl.col("count").sum().alias("total_readings"),
            pl.len().alias("window_count"),
            pl.col("comfort_index").mean().round(1).alias("avg_comfort")
                if "comfort_index" in df.columns
                else pl.lit(None).alias("avg_comfort"),
        ])
        .sort("overall_avg_temp", descending=True)
    )


def sliding_window_stats(
    df: pl.DataFrame,
    window_minutes: int = 5,
) -> pl.DataFrame:
    """
    Скользящее среднее температуры по каждому городу
    за последние window_minutes минут.
    """
    if len(df) == 0:
        return df

    return (
        df.sort(["city", "window_end"])
        .with_columns([
            pl.col("avg_temp")
              .rolling_mean(window_size=window_minutes,
                            min_periods=1)
              .over("city")
              .round(2)
              .alias(f"rolling_avg_temp_{window_minutes}w"),
        ])
    )


# ── Parquet I/O ──────────────────────────────────────────────────────────

def save_parquet(df: pl.DataFrame, path: str | Path) -> Path:
    """Сохраняет DataFrame в Parquet."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(p))
    size_kb = p.stat().st_size / 1024
    logger.info("Saved %d rows to %s (%.1f KB)", len(df), p, size_kb)
    return p


def load_parquet(path: str | Path) -> pl.DataFrame:
    """Загружает Parquet в DataFrame."""
    p = Path(path)
    if not p.exists():
        logger.warning("Parquet file not found: %s", p)
        return _empty_agg_df()
    df = pl.read_parquet(str(p))
    logger.info("Loaded %d rows from %s", len(df), p)
    return df


def append_parquet(
    new_records: list[WindowAggregate],
    path: str | Path,
) -> pl.DataFrame:
    """
    Добавляет новые записи к существующему Parquet-файлу.
    Удаляет дубликаты по (city, window_start).
    """
    existing = load_parquet(path)
    new_df = aggregates_to_df(new_records)
    if len(existing) == 0:
        combined = new_df
    else:
        combined = pl.concat([existing, new_df], how="diagonal")

    # Дедупликация: оставить последнюю запись на (city, window_start)
    deduped = (
        combined
        .sort("window_end", descending=True)
        .unique(subset=["city", "window_start"], keep="first")
        .sort(["city", "window_start"])
    )
    save_parquet(deduped, path)
    return deduped

=== py-analyzer/tests/test_transforms.py ===

"""Tests for Polars transforms."""
import polars as pl
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from analyzer.consumers import WindowAggregate
from analyzer.transforms import (
    aggregates_to_df, enrich, city_summary,
    sliding_window_stats, save_parquet, load_parquet,
    append_parquet,
)


def make_agg(city="Moscow", avg_temp=15.0, offset_min=0) -> WindowAggregate:
    now = datetime(2024, 1, 1, 12, 0, 0)
    return WindowAggregate(
        city=city,
        window_start=now + timedelta(minutes=offset_min),
        window_end=now + timedelta(minutes=offset_min + 1),
        count=6,
        avg_temp=avg_temp,
        min_temp=avg_temp - 2,
        max_temp=avg_temp + 2,
        avg_humidity=65.0,
        avg_pressure=1013.0,
        avg_wind_speed=5.0,
        shard_id="shard-0",
    )


def test_aggregates_to_df_empty():
    df = aggregates_to_df([])
    assert len(df) == 0
    assert "city" in df.columns


def test_aggregates_to_df_data():
    records = [make_agg("Moscow"), make_agg("London", avg_temp=18.0)]
    df = aggregates_to_df(records)
    assert len(df) == 2
    assert set(df["city"].to_list()) == {"Moscow", "London"}


def test_enrich_adds_columns():
    df = aggregates_to_df([make_agg()])
    enriched = enrich(df)
    assert "temp_range" in enriched.columns
    assert "comfort_index" in enriched.columns
    assert "window_duration_sec" in enriched.columns


def test_enrich_temp_range():
    df = aggregates_to_df([make_agg(avg_temp=15.0)])
    enriched = enrich(df)
    # max_temp=17, min_temp=13 → range=4
    assert enriched["temp_range"][0] == pytest.approx(4.0, abs=0.01)


def test_city_summary():
    records = [
        make_agg("Moscow", 10.0, 0),
        make_agg("Moscow", 20.0, 1),
        make_agg("London", 18.0, 0),
    ]
    df = enrich(aggregates_to_df(records))
    summary = city_summary(df)
    moscow = summary.filter(pl.col("city") == "Moscow")
    assert moscow["overall_avg_temp"][0] == pytest.approx(15.0, abs=0.1)
    assert moscow["window_count"][0] == 2


def test_sliding_window_stats():
    records = [make_agg("Moscow", t, i)
               for i, t in enumerate([10.0, 20.0, 30.0])]
    df = aggregates_to_df(records)
    result = sliding_window_stats(df, window_minutes=2)
    assert "rolling_avg_temp_2w" in result.columns
    assert len(result) == 3


def test_save_and_load_parquet(tmp_path):
    records = [make_agg("Moscow"), make_agg("London")]
    df = aggregates_to_df(records)
    path = tmp_path / "test.parquet"
    save_parquet(df, path)
    loaded = load_parquet(path)
    assert len(loaded) == 2
    assert set(loaded["city"].to_list()) == {"Moscow", "London"}


def test_load_parquet_missing(tmp_path):
    df = load_parquet(tmp_path / "nonexistent.parquet")
    assert len(df) == 0


def test_append_parquet_dedup(tmp_path):
    path = tmp_path / "weather.parquet"
    records1 = [make_agg("Moscow", 10.0, 0)]
    append_parquet(records1, path)
    # Добавляем дубликат + новую запись
    records2 = [make_agg("Moscow", 10.0, 0), make_agg("London", 18.0, 0)]
    result = append_parquet(records2, path)
    # Дубликат должен быть удалён
    assert len(result) == 2

ПРОВЕРКА:
  cd py-analyzer
  uv run pytest tests/test_transforms.py -v 2>&1
  cd ..

9 тестов зелёных.

prompts/05-2-transforms.md — этот промт целиком.
