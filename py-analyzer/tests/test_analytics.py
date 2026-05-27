"""Tests for DuckDB analytics."""
import pytest
from datetime import datetime, timedelta
import polars as pl

from analyzer.consumers import WindowAggregate
from analyzer.transforms import aggregates_to_df, enrich
from analyzer.analytics import WeatherAnalytics


def make_records(n_cities=3, n_windows=10) -> list[WindowAggregate]:
    cities = ["Moscow", "London", "Tokyo", "Berlin", "Stockholm"][:n_cities]
    records = []
    base = datetime(2024, 6, 1, 0, 0, 0)
    import random
    random.seed(42)
    for i in range(n_windows):
        for city in cities:
            base_temp = {"Moscow": 15, "London": 18,
                         "Tokyo": 25, "Berlin": 20,
                         "Stockholm": 12}.get(city, 15)
            t = base_temp + random.uniform(-3, 3)
            records.append(WindowAggregate(
                city=city,
                window_start=base + timedelta(minutes=i),
                window_end=base + timedelta(minutes=i + 1),
                count=6,
                avg_temp=round(t, 2),
                min_temp=round(t - 2, 2),
                max_temp=round(t + 2, 2),
                avg_humidity=round(random.uniform(50, 80), 1),
                avg_pressure=round(random.uniform(1005, 1020), 1),
                avg_wind_speed=round(random.uniform(1, 10), 1),
                shard_id="shard-0",
            ))
    return records


@pytest.fixture()
def df():
    return enrich(aggregates_to_df(make_records()))


@pytest.fixture()
def analytics():
    a = WeatherAnalytics()
    yield a
    a.close()


def test_top_cities(df, analytics):
    result = analytics.top_cities_by_temp(df, top_n=3)
    assert len(result) == 3
    assert "city" in result.columns
    assert "mean_temp" in result.columns
    # Tokyo должен быть теплее Moscow
    cities = result["city"].to_list()
    assert cities.index("Tokyo") < cities.index("Moscow")


def test_hourly_stats(df, analytics):
    result = analytics.hourly_stats(df)
    assert "hour_of_day" in result.columns
    assert len(result) >= 1


def test_temperature_percentiles(df, analytics):
    result = analytics.temperature_percentiles(df)
    assert "median" in result.columns
    assert len(result) == 3  # 3 города


def test_anomalies_returns_df(df, analytics):
    result = analytics.anomalies(df, z_threshold=1.0)
    assert isinstance(result, pl.DataFrame)
    # Может быть пустым если данных мало
    assert "z_score" in result.columns


def test_compare_performance(df, analytics):
    result = analytics.compare_polars_vs_duckdb(df, df)
    assert "duckdb_ms" in result
    assert "polars_ms" in result
    assert result["rows"] > 0


def test_context_manager():
    with WeatherAnalytics() as a:
        df = aggregates_to_df(make_records(n_cities=2, n_windows=3))
        result = a.top_cities_by_temp(df, top_n=2)
        assert len(result) == 2
