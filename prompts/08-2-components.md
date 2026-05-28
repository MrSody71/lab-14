Создай переиспользуемые компоненты дашборда —
графики и виджеты которые будут собраны в app.py.

=== dashboard/src/dashboard/components.py ===

"""
Streamlit-компоненты для weather pipeline дашборда.
Каждая функция принимает DataFrame и рендерит один блок.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
import streamlit as st


# ── Цветовая схема ────────────────────────────────────────────────────────

CITY_COLORS = {
    "Moscow":           "#E53935",
    "Saint-Petersburg": "#8E24AA",
    "Novosibirsk":      "#1E88E5",
    "Yekaterinburg":    "#00ACC1",
    "Kazan":            "#43A047",
    "Stockholm":        "#FFB300",
    "Berlin":           "#FB8C00",
    "London":           "#6D4C41",
    "New-York":         "#546E7A",
    "Tokyo":            "#F06292",
}


def _city_color(city: str) -> str:
    return CITY_COLORS.get(city, "#888888")


# ── KPI-карточки ──────────────────────────────────────────────────────────

def render_kpi_cards(df: pl.DataFrame) -> None:
    """
    Строка KPI-карточек: средняя температура, влажность,
    давление, ветер — усреднённые по последнему окну.
    """
    if len(df) == 0:
        st.warning("No data available")
        return

    # Берём последние записи (последнее окно для каждого города)
    latest = (
        df.sort("window_end", descending=True)
        .group_by("city")
        .head(1)
    )

    avg_temp  = latest["avg_temp"].mean()
    avg_hum   = latest["avg_humidity"].mean()
    avg_pres  = latest["avg_pressure"].mean()
    avg_wind  = latest["avg_wind_speed"].mean()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🌡️ Avg Temperature",
            value=f"{avg_temp:.1f} °C" if avg_temp else "N/A",
        )
    with col2:
        st.metric(
            label="💧 Avg Humidity",
            value=f"{avg_hum:.0f} %" if avg_hum else "N/A",
        )
    with col3:
        st.metric(
            label="🔵 Avg Pressure",
            value=f"{avg_pres:.0f} hPa" if avg_pres else "N/A",
        )
    with col4:
        st.metric(
            label="💨 Avg Wind",
            value=f"{avg_wind:.1f} m/s" if avg_wind else "N/A",
        )


# ── Температурный timeline ────────────────────────────────────────────────

def render_temperature_timeline(
    df: pl.DataFrame,
    selected_cities: list[str],
    hours: int = 1,
) -> None:
    """
    Линейный график avg_temp по времени для выбранных городов.
    Фильтрует по последним `hours` часам.
    """
    st.subheader("🌡️ Temperature Timeline")

    if len(df) == 0 or not selected_cities:
        st.info("Select cities above to see data")
        return

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    filtered = (
        df
        .filter(
            pl.col("city").is_in(selected_cities)
            & (pl.col("window_end") >= cutoff)
        )
        .sort("window_end")
    )

    if len(filtered) == 0:
        st.info("No data in selected time range")
        return

    pdf = filtered.to_pandas()
    fig = px.line(
        pdf,
        x="window_end",
        y="avg_temp",
        color="city",
        color_discrete_map=CITY_COLORS,
        labels={
            "window_end": "Time (UTC)",
            "avg_temp":   "Temperature (°C)",
        },
        template="plotly_white",
    )
    fig.update_traces(
        mode="lines+markers",
        marker_size=5,
        line_width=2,
    )
    fig.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=30, b=0),
        legend_title_text="",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Текущие температуры: горизонтальный bar chart ─────────────────────────

def render_current_temps(df: pl.DataFrame) -> None:
    """
    Горизонтальный bar chart текущих температур по всем городам.
    """
    st.subheader("📊 Current Temperature by City")

    if len(df) == 0:
        st.info("No data")
        return

    latest = (
        df.sort("window_end", descending=True)
        .group_by("city")
        .head(1)
        .sort("avg_temp", descending=True)
    )

    pdf = latest.to_pandas()
    colors = [_city_color(c) for c in pdf["city"].tolist()]

    fig = go.Figure(go.Bar(
        x=pdf["avg_temp"],
        y=pdf["city"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}°C" for v in pdf["avg_temp"]],
        textposition="outside",
    ))
    fig.update_layout(
        height=350,
        margin=dict(l=0, r=60, t=10, b=0),
        xaxis_title="Temperature (°C)",
        template="plotly_white",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Humidity + Wind heatmap ───────────────────────────────────────────────

def render_humidity_wind_scatter(df: pl.DataFrame) -> None:
    """
    Scatter plot: ось X = влажность, ось Y = скорость ветра,
    размер точки = температура, цвет = город.
    """
    st.subheader("💧 Humidity vs Wind Speed")

    if len(df) == 0:
        return

    latest = (
        df.sort("window_end", descending=True)
        .group_by("city")
        .head(1)
        .with_columns(
            (pl.col("avg_temp") + 50.0).clip(1.0, None).alias("_size")
        )
    )

    pdf = latest.to_pandas()
    fig = px.scatter(
        pdf,
        x="avg_humidity",
        y="avg_wind_speed",
        color="city",
        size="_size",
        size_max=25,
        color_discrete_map=CITY_COLORS,
        hover_data=["city", "avg_temp",
                    "avg_humidity", "avg_wind_speed"],
        labels={
            "avg_humidity":   "Humidity (%)",
            "avg_wind_speed": "Wind Speed (m/s)",
        },
        template="plotly_white",
    )
    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        legend_title_text="",
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Gauge: комфортность ───────────────────────────────────────────────────

def render_comfort_gauges(
    df: pl.DataFrame,
    cities: list[str],
) -> None:
    """
    Gauge-диаграммы индекса комфорта для выбранных городов.
    """
    st.subheader("😊 Comfort Index")

    if len(df) == 0 or not cities:
        return

    latest = (
        df.sort("window_end", descending=True)
        .filter(pl.col("city").is_in(cities))
        .group_by("city")
        .head(1)
        .with_columns([
            (
                100
                - (pl.col("avg_temp") - 18.0).abs() * 2
                - (pl.col("avg_humidity") - 50.0).abs() * 0.3
                - pl.col("avg_wind_speed") * 1.5
            ).clip(0, 100).round(1).alias("comfort")
        ])
        .sort("comfort", descending=True)
    )

    show_cities = latest["city"].to_list()[:4]
    cols = st.columns(len(show_cities))

    for col, row in zip(
        cols,
        latest.filter(
            pl.col("city").is_in(show_cities)
        ).iter_rows(named=True),
    ):
        comfort = row["comfort"]
        color = (
            "green" if comfort >= 70
            else "orange" if comfort >= 40
            else "red"
        )
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=comfort,
            title={"text": row["city"], "font": {"size": 12}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar":  {"color": color},
                "steps": [
                    {"range": [0, 40],   "color": "#ffebee"},
                    {"range": [40, 70],  "color": "#fff9c4"},
                    {"range": [70, 100], "color": "#e8f5e9"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 2},
                    "thickness": 0.75,
                    "value": 70,
                },
            },
            number={"suffix": "", "font": {"size": 20}},
        ))
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        col.plotly_chart(fig, use_container_width=True)


# ── Таблица последних данных ──────────────────────────────────────────────

def render_data_table(
    df: pl.DataFrame,
    n_rows: int = 20,
) -> None:
    """Таблица последних N записей."""
    st.subheader("📋 Latest Records")

    if len(df) == 0:
        st.info("No data")
        return

    display = (
        df.sort("window_end", descending=True)
        .head(n_rows)
        .select([
            "city", "window_end",
            "avg_temp", "min_temp", "max_temp",
            "avg_humidity", "avg_pressure",
            "avg_wind_speed", "count",
        ])
        .with_columns([
            pl.col("avg_temp").round(1),
            pl.col("min_temp").round(1),
            pl.col("max_temp").round(1),
            pl.col("avg_humidity").round(0).cast(pl.Int64),
            pl.col("avg_pressure").round(0).cast(pl.Int64),
            pl.col("avg_wind_speed").round(1),
        ])
    )
    st.dataframe(
        display.to_pandas(),
        use_container_width=True,
        hide_index=True,
    )

=== dashboard/tests/test_components.py ===

"""Smoke-тесты компонентов — проверяем что не падают."""
import pytest
import polars as pl
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from dashboard.data import generate_mock_batch


# Мокаем streamlit чтобы тесты работали без GUI
import sys
_st_mock = MagicMock()
_st_mock.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]
sys.modules["streamlit"] = _st_mock

from dashboard import components


@pytest.fixture()
def df():
    return generate_mock_batch(n_cities=3, n_windows=10)


def test_render_kpi_cards_no_crash(df):
    """render_kpi_cards не должен бросать исключение."""
    try:
        components.render_kpi_cards(df)
    except Exception as e:
        pytest.fail(f"render_kpi_cards raised: {e}")


def test_render_kpi_cards_empty():
    from dashboard.data import empty_df
    components.render_kpi_cards(empty_df())


def test_render_temperature_timeline_no_crash(df):
    components.render_temperature_timeline(
        df, ["Moscow", "London"], hours=24
    )


def test_render_current_temps_no_crash(df):
    components.render_current_temps(df)


def test_render_humidity_wind_scatter_no_crash(df):
    components.render_humidity_wind_scatter(df)


def test_render_comfort_gauges_no_crash(df):
    components.render_comfort_gauges(df, ["Moscow", "London"])


def test_render_data_table_no_crash(df):
    components.render_data_table(df, n_rows=10)


def test_city_color_known():
    assert components._city_color("Moscow") == "#E53935"


def test_city_color_unknown():
    color = components._city_color("Atlantis")
    assert color.startswith("#")

ПРОВЕРКА:
  cd dashboard
  uv run pytest tests/test_components.py -v 2>&1
  cd ..

9 тестов зелёных.

prompts/08-2-components.md — этот промт целиком.
