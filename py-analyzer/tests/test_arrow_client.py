"""Tests for Arrow Flight client — uses a mock pyarrow Flight server."""

import threading

import polars as pl
import pyarrow as pa
import pyarrow.flight as flight
import pytest

from analyzer.arrow_client import WeatherFlightClient, _empty_df


# ── Минимальный in-process Flight сервер для тестов ──────────────────────

class _MockFlightServer(flight.FlightServerBase):
    def __init__(self, records: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._table = pa.table(records)

    def do_get(self, context, ticket):
        return flight.RecordBatchStream(self._table)


@pytest.fixture()
def mock_server():
    """Поднимает Flight сервер на случайном порту, останавливает после теста."""
    records = {
        "city":           pa.array(["Moscow", "London"]),
        "window_start":   pa.array([1700000000, 1700000060], type=pa.int64()),
        "window_end":     pa.array([1700000060, 1700000120], type=pa.int64()),
        "count":          pa.array([5, 3], type=pa.int32()),
        "avg_temp":       pa.array([12.5, 18.0]),
        "min_temp":       pa.array([10.0, 15.0]),
        "max_temp":       pa.array([15.0, 21.0]),
        "avg_humidity":   pa.array([65.0, 72.0]),
        "avg_pressure":   pa.array([1013.0, 1008.0]),
        "avg_wind_speed": pa.array([4.5, 6.2]),
        "shard_id":       pa.array(["shard-0", "shard-0"]),
    }
    server = _MockFlightServer(
        records,
        location=flight.Location.for_grpc_tcp("localhost", 0),
    )
    port = server.port
    t = threading.Thread(target=server.serve, daemon=True)
    t.start()
    yield port
    server.shutdown()


# ── Тесты ─────────────────────────────────────────────────────────────────

def test_fetch_all_returns_dataframe(mock_server):
    client = WeatherFlightClient("localhost", mock_server)
    client.connect()
    df = client.fetch_all()
    client.close()
    assert len(df) == 2
    assert "city" in df.columns
    assert "avg_temp" in df.columns


def test_fetch_all_cities(mock_server):
    with WeatherFlightClient("localhost", mock_server) as client:
        df = client.fetch_all()
    assert set(df["city"].to_list()) == {"Moscow", "London"}


def test_empty_df_schema():
    df = _empty_df()
    assert len(df) == 0
    assert "avg_temp" in df.columns
    assert df["avg_temp"].dtype == pl.Float64


def test_not_connected_raises():
    client = WeatherFlightClient("localhost", 19999)
    with pytest.raises(RuntimeError, match="Not connected"):
        client.fetch_all()
