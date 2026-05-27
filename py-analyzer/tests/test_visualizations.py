"""Tests for visualization module — checks files are created."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import polars as pl

from analyzer.consumers import WindowAggregate
from analyzer.transforms import aggregates_to_df, enrich
from analyzer.visualizations import (
    plot_temperature_timeline,
    plot_temperature_histogram,
    plot_humidity_heatmap,
    plot_performance_comparison,
    plot_comfort_index,
)


def make_df(n=20) -> pl.DataFrame:
    import random
    random.seed(7)
    records = []
    base = datetime(2024, 6, 1, 8, 0, 0)
    for i in range(n):
        for city in ["Moscow", "London", "Tokyo"]:
            t = {"Moscow":15,"London":18,"Tokyo":25}[city]
            records.append(WindowAggregate(
                city=city,
                window_start=base + timedelta(minutes=i*5),
                window_end=base + timedelta(minutes=i*5+5),
                count=6,
                avg_temp=round(t + random.uniform(-2,2), 2),
                min_temp=t - 2, max_temp=t + 2,
                avg_humidity=round(random.uniform(50,80),1),
                avg_pressure=round(random.uniform(1005,1020),1),
                avg_wind_speed=round(random.uniform(1,8),1),
                shard_id="shard-0",
            ))
    return enrich(aggregates_to_df(records))


@pytest.fixture()
def df():
    return make_df()


def test_temperature_timeline(df, tmp_path):
    path = plot_temperature_timeline(df, output_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".html"
    assert path.stat().st_size > 1000


def test_temperature_histogram(df, tmp_path):
    path = plot_temperature_histogram(df, output_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".png"
    assert path.stat().st_size > 1000


def test_humidity_heatmap(df, tmp_path):
    path = plot_humidity_heatmap(df, output_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".html"


def test_performance_comparison(tmp_path):
    results = [
        {"rows": 100,  "duckdb_ms": 1.2, "polars_ms": 0.8},
        {"rows": 1000, "duckdb_ms": 2.5, "polars_ms": 1.1},
        {"rows": 5000, "duckdb_ms": 4.1, "polars_ms": 2.3},
    ]
    path = plot_performance_comparison(results, output_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".png"


def test_comfort_index(df, tmp_path):
    path = plot_comfort_index(df, output_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".html"
