"""
Polars-трансформации для weather pipeline.
Принимает list[WindowAggregate] → DataFrame → Parquet.
"""
from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from analyzer.consumers import WindowAggregate

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
        (pl.col("window_end") - pl.col("window_start"))
            .dt.total_seconds()
            .alias("window_duration_sec"),

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

    comfort_expr = (
        pl.col("comfort_index").mean().round(1).alias("avg_comfort")
        if "comfort_index" in df.columns
        else pl.lit(None).alias("avg_comfort")
    )

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
            comfort_expr,
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
    combined = new_df if len(existing) == 0 else pl.concat([existing, new_df], how="diagonal")

    # Дедупликация: оставить последнюю запись на (city, window_start)
    deduped = (
        combined
        .sort("window_end", descending=True)
        .unique(subset=["city", "window_start"], keep="first")
        .sort(["city", "window_start"])
    )
    save_parquet(deduped, path)
    return deduped
