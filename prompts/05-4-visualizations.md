Реализуй модуль визуализации — минимум 4 графика,
сохраняемых в файлы.

=== py-analyzer/src/analyzer/visualizations.py ===

"""
Визуализации для weather pipeline.
Plotly для интерактивных HTML, Matplotlib для PNG.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/plots")


def _ensure_output(path: Optional[Path] = None) -> Path:
    p = path or OUTPUT_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── График 1: Временной ряд температуры по городам (Plotly) ──────────────

def plot_temperature_timeline(
    df: pl.DataFrame,
    output_dir: Optional[Path] = None,
    cities: Optional[list[str]] = None,
) -> Path:
    """
    Линейный график avg_temp по времени для каждого города.
    Сохраняет интерактивный HTML.
    """
    out = _ensure_output(output_dir)

    pdf = df.to_pandas()
    if cities:
        pdf = pdf[pdf["city"].isin(cities)]

    fig = px.line(
        pdf,
        x="window_end",
        y="avg_temp",
        color="city",
        title="Average Temperature Timeline by City",
        labels={"window_end": "Time", "avg_temp": "Avg Temperature (°C)"},
        template="plotly_white",
    )
    fig.update_traces(mode="lines+markers", marker_size=4)
    fig.update_layout(
        legend_title_text="City",
        hovermode="x unified",
        height=500,
    )

    path = out / "temperature_timeline.html"
    fig.write_html(str(path))
    logger.info("Saved temperature timeline to %s", path)
    return path


# ── График 2: Гистограмма распределения температур (Matplotlib) ──────────

def plot_temperature_histogram(
    df: pl.DataFrame,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Гистограмма распределения avg_temp по городам.
    Сохраняет PNG.
    """
    out = _ensure_output(output_dir)

    fig, ax = plt.subplots(figsize=(10, 6))
    cities = df["city"].unique().to_list()
    colors = plt.cm.tab10.colors

    for i, city in enumerate(sorted(cities)):
        temps = df.filter(pl.col("city") == city)["avg_temp"].to_list()
        ax.hist(
            temps,
            bins=15,
            alpha=0.6,
            label=city,
            color=colors[i % len(colors)],
            edgecolor="white",
            linewidth=0.5,
        )

    ax.set_xlabel("Average Temperature (°C)", fontsize=12)
    ax.set_ylabel("Frequency", fontsize=12)
    ax.set_title("Temperature Distribution by City", fontsize=14)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    path = out / "temperature_histogram.png"
    fig.savefig(str(path), dpi=150)
    plt.close(fig)
    logger.info("Saved temperature histogram to %s", path)
    return path


# ── График 3: Heatmap влажности по городам и часам (Plotly) ──────────────

def plot_humidity_heatmap(
    df: pl.DataFrame,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Тепловая карта: ось X — час суток, ось Y — город,
    цвет — средняя влажность.
    """
    out = _ensure_output(output_dir)

    # Добавляем колонку часа
    pivot_df = (
        df.with_columns(
            pl.col("window_end").dt.hour().alias("hour")
        )
        .group_by(["city", "hour"])
        .agg(pl.col("avg_humidity").mean().round(1).alias("humidity"))
        .sort(["city", "hour"])
    )

    pdf = pivot_df.to_pandas().pivot(
        index="city", columns="hour", values="humidity"
    )

    fig = go.Figure(data=go.Heatmap(
        z=pdf.values.tolist(),
        x=[str(h) + ":00" for h in pdf.columns.tolist()],
        y=pdf.index.tolist(),
        colorscale="Blues",
        colorbar_title="Humidity %",
        hoverongaps=False,
    ))
    fig.update_layout(
        title="Average Humidity by City and Hour of Day",
        xaxis_title="Hour of Day",
        yaxis_title="City",
        template="plotly_white",
        height=400,
    )

    path = out / "humidity_heatmap.html"
    fig.write_html(str(path))
    logger.info("Saved humidity heatmap to %s", path)
    return path


# ── График 4: Сравнение производительности DuckDB vs Polars (Matplotlib) ─

def plot_performance_comparison(
    results: list[dict],
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Столбчатый график сравнения времени выполнения
    DuckDB vs Polars для разных размеров датасета.

    results: [{rows: int, duckdb_ms: float, polars_ms: float}, ...]
    """
    out = _ensure_output(output_dir)

    rows = [r["rows"] for r in results]
    duckdb_ms = [r["duckdb_ms"] for r in results]
    polars_ms = [r["polars_ms"] for r in results]

    x = range(len(rows))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar([i - width/2 for i in x], duckdb_ms,
                   width, label="DuckDB", color="#2196F3", alpha=0.85)
    bars2 = ax.bar([i + width/2 for i in x], polars_ms,
                   width, label="Polars", color="#FF9800", alpha=0.85)

    ax.set_xlabel("Dataset Size (rows)", fontsize=12)
    ax.set_ylabel("Execution Time (ms)", fontsize=12)
    ax.set_title("DuckDB vs Polars: Aggregation Performance", fontsize=14)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{r:,}" for r in rows])
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # Подписи над столбцами
    for bar in list(bars1) + list(bars2):
        h = bar.get_height()
        ax.annotate(f"{h:.1f}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    path = out / "performance_comparison.png"
    fig.savefig(str(path), dpi=150)
    plt.close(fig)
    logger.info("Saved performance comparison to %s", path)
    return path


# ── График 5: Comfort index по городам (Plotly bar) ──────────────────────

def plot_comfort_index(
    df: pl.DataFrame,
    output_dir: Optional[Path] = None,
) -> Path:
    """Столбчатый график среднего индекса комфорта по городам."""
    out = _ensure_output(output_dir)

    if "comfort_index" not in df.columns:
        from analyzer.transforms import enrich
        df = enrich(df)

    summary = (
        df.group_by("city")
        .agg(pl.col("comfort_index").mean().round(1).alias("avg_comfort"))
        .sort("avg_comfort", descending=True)
    )

    fig = px.bar(
        summary.to_pandas(),
        x="city",
        y="avg_comfort",
        color="avg_comfort",
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        title="Average Comfort Index by City",
        labels={"avg_comfort": "Comfort Index (0-100)", "city": "City"},
        template="plotly_white",
    )
    fig.update_layout(
        showlegend=False,
        height=450,
        coloraxis_showscale=True,
    )

    path = out / "comfort_index.html"
    fig.write_html(str(path))
    logger.info("Saved comfort index chart to %s", path)
    return path

=== py-analyzer/tests/test_visualizations.py ===

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

ПРОВЕРКА:
  cd py-analyzer
  uv run pytest tests/test_visualizations.py -v 2>&1
  cd ..

5 тестов зелёных. Каждый тест проверяет что файл создан и не пустой.

prompts/05-4-visualizations.md — этот промт целиком.
