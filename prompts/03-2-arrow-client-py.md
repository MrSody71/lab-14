Прочитай CLAUDE.md.

Реализуй Arrow Flight клиент в py-analyzer.
Клиент подключается к Go-серверу и получает данные как Arrow RecordBatch,
который сразу конвертируется в Polars DataFrame.

=== py-analyzer/src/analyzer/arrow_client.py ===

"""Arrow Flight client for weather pipeline."""

from __future__ import annotations

import logging
from typing import Optional

import polars as pl
import pyarrow as pa
import pyarrow.flight as flight

logger = logging.getLogger(__name__)


class WeatherFlightClient:
    """Клиент Apache Arrow Flight для получения агрегатов погоды."""

    def __init__(self, host: str = "localhost", port: int = 8815) -> None:
        self._addr = f"grpc://{host}:{port}"
        self._client: Optional[flight.FlightClient] = None

    def connect(self) -> None:
        self._client = flight.connect(self._addr)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "WeatherFlightClient":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def fetch_all(self) -> pl.DataFrame:
        return self._fetch(b"all")

    def fetch_city(self, city: str) -> pl.DataFrame:
        return self._fetch(city.encode())

    def _fetch(self, ticket_bytes: bytes) -> pl.DataFrame:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")
        ticket = flight.Ticket(ticket_bytes)
        reader = self._client.do_get(ticket)
        table: pa.Table = reader.read_all()
        if table.num_rows == 0:
            return _empty_df()
        df = pl.from_arrow(table)
        for col in ("window_start", "window_end"):
            if col in df.columns:
                df = df.with_columns(
                    pl.from_epoch(pl.col(col).cast(pl.Int64), time_unit="s").alias(col)
                )
        return df


def _empty_df() -> pl.DataFrame:
    return pl.DataFrame({
        "city": pl.Series([], dtype=pl.String),
        "window_start": pl.Series([], dtype=pl.Datetime),
        "window_end": pl.Series([], dtype=pl.Datetime),
        "count": pl.Series([], dtype=pl.Int32),
        "avg_temp": pl.Series([], dtype=pl.Float64),
        "min_temp": pl.Series([], dtype=pl.Float64),
        "max_temp": pl.Series([], dtype=pl.Float64),
        "avg_humidity": pl.Series([], dtype=pl.Float64),
        "avg_pressure": pl.Series([], dtype=pl.Float64),
        "avg_wind_speed": pl.Series([], dtype=pl.Float64),
        "shard_id": pl.Series([], dtype=pl.String),
    })

=== py-analyzer/tests/test_arrow_client.py ===

Тесты через in-process mock FlightServerBase.

Примечание: в pyarrow 24 FlightServerBase не имеет метода init() —
порт выделяется при создании объекта (location=for_grpc_tcp("localhost", 0)),
читается через server.port.

test_fetch_all_returns_dataframe — 2 строки, есть city и avg_temp
test_fetch_all_cities — set(df["city"]) == {"Moscow", "London"}
test_empty_df_schema — len==0, dtype avg_temp == pl.Float64
test_not_connected_raises — RuntimeError "Not connected"

ПРОВЕРКА:
  cd py-analyzer
  uv run pytest tests/test_arrow_client.py -v 2>&1

4 теста зелёных.

prompts/03-2-arrow-client-py.md — этот промт целиком.
