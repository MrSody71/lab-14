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
        """Установить соединение с Flight сервером."""
        self._client = flight.connect(self._addr)
        logger.info("Connected to Arrow Flight server at %s", self._addr)

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
        """Получить все агрегаты с сервера как Polars DataFrame."""
        return self._fetch(b"all")

    def fetch_city(self, city: str) -> pl.DataFrame:
        """Получить агрегаты для конкретного города."""
        return self._fetch(city.encode())

    def _fetch(self, ticket_bytes: bytes) -> pl.DataFrame:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        ticket = flight.Ticket(ticket_bytes)
        reader = self._client.do_get(ticket)
        table: pa.Table = reader.read_all()

        if table.num_rows == 0:
            logger.warning("Received empty table from Flight server")
            return _empty_df()

        df = pl.from_arrow(table)
        # Конвертируем timestamp колонки из unix seconds в datetime
        for col in ("window_start", "window_end"):
            if col in df.columns:
                df = df.with_columns(
                    pl.from_epoch(pl.col(col).cast(pl.Int64),
                                  time_unit="s").alias(col)
                )
        logger.info("Fetched %d rows from Flight server", len(df))
        return df


def _empty_df() -> pl.DataFrame:
    """Вернуть пустой DataFrame с правильной схемой."""
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
