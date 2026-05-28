"""
DuckDB-аналитика поверх Parquet-файлов weather pipeline.
Все запросы принимают путь к parquet-файлу или DataFrame.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import duckdb
import polars as pl

logger = logging.getLogger(__name__)

# Тип: путь к parquet или уже загруженный DataFrame
DataSource = str | Path | pl.DataFrame


def _get_source_expr(source: DataSource, conn: duckdb.DuckDBPyConnection) -> str:
    """
    Возвращает SQL-выражение источника для подстановки в FROM.
    Если DataFrame — регистрирует его как временную таблицу.
    """
    if isinstance(source, pl.DataFrame):
        conn.register("_df_source", source.to_arrow())
        return "_df_source"
    return f"'{source}'"


class WeatherAnalytics:
    """DuckDB-аналитика для weather pipeline."""

    def __init__(self) -> None:
        # In-memory база, пересоздаётся при каждом запросе
        self._conn = duckdb.connect()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> WeatherAnalytics:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _query(self, sql: str, source: DataSource) -> pl.DataFrame:
        """Выполняет SQL и возвращает Polars DataFrame. Логирует время."""
        src = _get_source_expr(source, self._conn)
        full_sql = sql.replace("{src}", src)
        t0 = time.perf_counter()
        result = self._conn.execute(full_sql).pl()
        elapsed = (time.perf_counter() - t0) * 1000
        logger.debug("Query executed in %.1f ms, %d rows", elapsed, len(result))
        return result

    # ── Запросы ───────────────────────────────────────────────────────────

    def top_cities_by_temp(
        self, source: DataSource, top_n: int = 5
    ) -> pl.DataFrame:
        """Топ N городов по средней температуре."""
        return self._query(f"""
            SELECT
                city,
                ROUND(AVG(avg_temp), 2)      AS mean_temp,
                ROUND(MIN(min_temp), 2)      AS abs_min_temp,
                ROUND(MAX(max_temp), 2)      AS abs_max_temp,
                SUM(count)                   AS total_readings,
                COUNT(*)                     AS window_count
            FROM {{src}}
            GROUP BY city
            ORDER BY mean_temp DESC
            LIMIT {top_n}
        """, source)

    def hourly_stats(self, source: DataSource) -> pl.DataFrame:
        """Статистика по часам суток (усреднение по всем городам)."""
        return self._query("""
            SELECT
                HOUR(window_start)           AS hour_of_day,
                ROUND(AVG(avg_temp), 2)      AS avg_temp,
                ROUND(AVG(avg_humidity), 1)  AS avg_humidity,
                ROUND(AVG(avg_wind_speed),2) AS avg_wind,
                COUNT(*)                     AS samples
            FROM {src}
            GROUP BY hour_of_day
            ORDER BY hour_of_day
        """, source)

    def temperature_percentiles(self, source: DataSource) -> pl.DataFrame:
        """Перцентили температуры по каждому городу."""
        return self._query("""
            SELECT
                city,
                ROUND(PERCENTILE_CONT(0.05)
                    WITHIN GROUP (ORDER BY avg_temp), 2) AS p05,
                ROUND(PERCENTILE_CONT(0.25)
                    WITHIN GROUP (ORDER BY avg_temp), 2) AS p25,
                ROUND(PERCENTILE_CONT(0.50)
                    WITHIN GROUP (ORDER BY avg_temp), 2) AS median,
                ROUND(PERCENTILE_CONT(0.75)
                    WITHIN GROUP (ORDER BY avg_temp), 2) AS p75,
                ROUND(PERCENTILE_CONT(0.95)
                    WITHIN GROUP (ORDER BY avg_temp), 2) AS p95
            FROM {src}
            GROUP BY city
            ORDER BY median DESC
        """, source)

    def anomalies(
        self,
        source: DataSource,
        z_threshold: float = 2.0,
    ) -> pl.DataFrame:
        """
        Аномальные показания: отклонение от среднего города
        более чем на z_threshold стандартных отклонений.
        """
        return self._query(f"""
            WITH city_stats AS (
                SELECT
                    city,
                    AVG(avg_temp)    AS mean_t,
                    STDDEV(avg_temp) AS std_t
                FROM {{src}}
                GROUP BY city
            )
            SELECT
                s.city,
                s.window_start,
                s.avg_temp,
                ROUND(ABS(s.avg_temp - cs.mean_t)
                      / NULLIF(cs.std_t, 0), 2) AS z_score
            FROM {{src}} s
            JOIN city_stats cs ON s.city = cs.city
            WHERE ABS(s.avg_temp - cs.mean_t)
                  / NULLIF(cs.std_t, 0) > {z_threshold}
            ORDER BY z_score DESC
        """, source)

    def compare_polars_vs_duckdb(
        self,
        source: DataSource,
        df: pl.DataFrame,
    ) -> dict:
        """
        Замеряет время выполнения одного агрегата в Polars и DuckDB.
        Возвращает dict с временами в мс.
        """
        # DuckDB
        t0 = time.perf_counter()
        self._query("""
            SELECT city, ROUND(AVG(avg_temp),2) AS mean_temp
            FROM {src}
            GROUP BY city ORDER BY mean_temp DESC
        """, source)
        duckdb_ms = (time.perf_counter() - t0) * 1000

        # Polars
        t0 = time.perf_counter()
        (
            df.group_by("city")
            .agg(pl.col("avg_temp").mean().round(2))
            .sort("avg_temp", descending=True)
        )
        polars_ms = (time.perf_counter() - t0) * 1000

        result = {
            "duckdb_ms": round(duckdb_ms, 3),
            "polars_ms": round(polars_ms, 3),
            "rows": len(df),
        }
        logger.info("Performance: DuckDB=%.1fms Polars=%.1fms rows=%d",
                    duckdb_ms, polars_ms, len(df))
        return result
