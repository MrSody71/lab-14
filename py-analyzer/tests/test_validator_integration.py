"""Tests for validator.py — Polars DataFrame validation pipeline."""
import time

import polars as pl

from analyzer.validator import validate_dataframe

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
