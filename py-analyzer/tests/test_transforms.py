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
