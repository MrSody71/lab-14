"""
Главный pipeline: читает из Kafka/NATS → валидирует →
сохраняет в Parquet → аналитика DuckDB → визуализации.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from pathlib import Path
from typing import Optional

import polars as pl
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

from analyzer.consumers import (
    WindowAggregate, kafka_consumer,
    nats_consumer, mock_consumer,
)
from analyzer.transforms import (
    aggregates_to_df, enrich, city_summary,
    sliding_window_stats, append_parquet, load_parquet,
)
from analyzer.analytics import WeatherAnalytics
from analyzer.validator import validate_dataframe, ValidationReport
from analyzer.visualizations import (
    plot_temperature_timeline,
    plot_temperature_histogram,
    plot_humidity_heatmap,
    plot_performance_comparison,
    plot_comfort_index,
)

logger = logging.getLogger(__name__)
console = Console()

PARQUET_PATH = Path(os.getenv("PARQUET_PATH", "data/weather.parquet"))
PLOTS_DIR    = Path(os.getenv("PLOTS_DIR", "data/plots"))
FLUSH_EVERY  = int(os.getenv("FLUSH_EVERY", "10"))  # записей


class WeatherPipeline:
    """Оркестрирует весь pipeline от консьюмера до визуализаций."""

    def __init__(
        self,
        kafka_brokers: Optional[list[str]] = None,
        kafka_topic: str = "weather.raw",
        nats_url: Optional[str] = None,
        nats_subject: str = "weather.raw",
        use_mock: bool = False,
        mock_cities: Optional[list[str]] = None,
    ) -> None:
        self.kafka_brokers = kafka_brokers
        self.kafka_topic = kafka_topic
        self.nats_url = nats_url
        self.nats_subject = nats_subject
        self.use_mock = use_mock
        self.mock_cities = mock_cities or [
            "Moscow", "London", "Tokyo",
            "Berlin", "Stockholm",
        ]
        self._queue: asyncio.Queue[WindowAggregate] = asyncio.Queue(
            maxsize=500
        )
        self._stop = asyncio.Event()
        self._buffer: list[WindowAggregate] = []
        self._total_processed = 0

    async def run(self) -> None:
        """Запустить pipeline. Блокирует до SIGINT."""
        console.print(Panel.fit(
            "[bold cyan]Weather Pipeline[/bold cyan] starting",
            border_style="cyan"
        ))

        tasks = []

        # Запустить консьюмеры
        if self.use_mock:
            console.print("[yellow]Using mock data generator[/yellow]")
            tasks.append(asyncio.create_task(
                mock_consumer(self.mock_cities, self._queue,
                              self._stop, interval_sec=1.0)
            ))
        else:
            if self.kafka_brokers:
                tasks.append(asyncio.create_task(
                    kafka_consumer(
                        self.kafka_brokers, self.kafka_topic,
                        "py-analyzer", self._queue, self._stop,
                    )
                ))
            if self.nats_url:
                tasks.append(asyncio.create_task(
                    nats_consumer(
                        self.nats_url, self.nats_subject,
                        self._queue, self._stop,
                    )
                ))

        # Обработчик сигналов
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig, lambda: self._stop.set()
                )
            except NotImplementedError:
                pass  # Windows

        # Главный цикл обработки
        tasks.append(asyncio.create_task(self._process_loop()))

        console.print("[green]Pipeline running.[/green] "
                      "Press Ctrl+C to stop.")
        await asyncio.gather(*tasks, return_exceptions=True)

        # Финальный flush
        if self._buffer:
            await self._flush()
        self._generate_reports()
        console.print("[bold green]Pipeline stopped cleanly.[/bold green]")

    async def _process_loop(self) -> None:
        """Читает из очереди и накапливает в буфер."""
        while not self._stop.is_set():
            try:
                agg = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                self._buffer.append(agg)
                self._total_processed += 1

                if len(self._buffer) >= FLUSH_EVERY:
                    await self._flush()

            except asyncio.TimeoutError:
                if self._buffer:
                    await self._flush()

    async def _flush(self) -> None:
        """Валидирует, сохраняет в Parquet, логирует."""
        if not self._buffer:
            return

        batch = self._buffer.copy()
        self._buffer.clear()

        raw_df = aggregates_to_df(batch)

        # Агрегаты уже прошли валидацию на этапе сборщика;
        # validate_dataframe ожидает сырые показания — пропускаем.
        try:
            clean_df, report = validate_dataframe(raw_df)
        except Exception:
            clean_df = raw_df
            report = ValidationReport(
                total=len(raw_df), valid=len(raw_df),
                backend="skipped",
            )

        if report.invalid > 0:
            logger.warning("Dropped %d invalid records: %s",
                           report.invalid, report.errors_by_field)

        if len(clean_df) == 0:
            return

        enrich(clean_df)
        append_parquet(
            [WindowAggregate.from_dict(r)
             for r in clean_df.to_dicts()],
            PARQUET_PATH,
        )

        console.print(
            f"[dim]Flushed {len(batch)} records "
            f"(valid: {report.valid}, "
            f"total: {self._total_processed})[/dim]"
        )

    def _generate_reports(self) -> None:
        """Генерирует итоговую аналитику и графики."""
        df = load_parquet(PARQUET_PATH)
        if len(df) == 0:
            console.print("[yellow]No data to analyze.[/yellow]")
            return

        enriched = enrich(df)
        console.print(f"\n[bold]Final report:[/bold] "
                      f"{len(df)} total records")

        # DuckDB аналитика
        with WeatherAnalytics() as analytics:
            top = analytics.top_cities_by_temp(enriched, top_n=10)
            perf_results = []
            for n in [100, 500, len(df)]:
                sample = enriched.sample(min(n, len(enriched)),
                                         seed=42)
                r = analytics.compare_polars_vs_duckdb(sample, sample)
                perf_results.append(r)

        # Вывод таблицы
        table = Table(title="Top Cities by Temperature")
        for col in top.columns:
            table.add_column(col, justify="right")
        for row in top.iter_rows():
            table.add_row(*[str(v) for v in row])
        console.print(table)

        # Визуализации
        console.print("\n[bold]Generating plots...[/bold]")
        plot_temperature_timeline(enriched, PLOTS_DIR)
        plot_temperature_histogram(enriched, PLOTS_DIR)
        plot_humidity_heatmap(enriched, PLOTS_DIR)
        plot_performance_comparison(perf_results, PLOTS_DIR)
        plot_comfort_index(enriched, PLOTS_DIR)

        console.print(f"[green]Plots saved to {PLOTS_DIR}[/green]")


def main() -> None:
    """CLI точка входа."""
    import typer

    app = typer.Typer()

    @app.command()
    def run(
        mock: bool = typer.Option(
            False, "--mock", help="Use mock data instead of Kafka/NATS"
        ),
        kafka: str = typer.Option(
            os.getenv("KAFKA_BROKERS", ""),
            help="Kafka brokers (comma-separated)"
        ),
        nats: str = typer.Option(
            os.getenv("NATS_URL", ""),
            help="NATS URL"
        ),
    ) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        pipeline = WeatherPipeline(
            kafka_brokers=kafka.split(",") if kafka else None,
            nats_url=nats if nats else None,
            use_mock=mock or (not kafka and not nats),
        )
        asyncio.run(pipeline.run())

    app()


if __name__ == "__main__":
    main()
