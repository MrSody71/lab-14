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
