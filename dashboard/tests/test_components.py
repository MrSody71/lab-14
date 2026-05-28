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
