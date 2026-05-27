"""
Демо-скрипт: подключается к Arrow Flight серверу и печатает данные.
Запуск: uv run python -m analyzer.demo_arrow
"""

import logging
import os

import polars as pl
from rich.console import Console
from rich.table import Table

from analyzer.arrow_client import WeatherFlightClient

logging.basicConfig(level=logging.INFO)
console = Console()


def main() -> None:
    host = os.getenv("ARROW_FLIGHT_HOST", "localhost")
    port = int(os.getenv("ARROW_FLIGHT_PORT", "8815"))

    console.print(
        f"[bold]Connecting to Arrow Flight server[/bold] at {host}:{port}"
    )

    try:
        with WeatherFlightClient(host, port) as client:
            df = client.fetch_all()
    except Exception as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        console.print(
            "Is the arrow-server running? "
            "Try: go run ./arrow-server/cmd/arrowsrv"
        )
        return

    if len(df) == 0:
        console.print(
            "[yellow]No data yet.[/yellow] "
            "Start the go-collector to generate aggregates."
        )
        return

    console.print(f"\n[green]Received {len(df)} rows[/green]\n")

    # Топ городов по средней температуре
    top = (
        df.group_by("city")
        .agg(
            pl.col("avg_temp").mean().round(2).alias("mean_temp"),
            pl.col("count").sum().alias("total_readings"),
        )
        .sort("mean_temp", descending=True)
    )

    table = Table(title="Weather Summary by City")
    table.add_column("City", style="cyan")
    table.add_column("Mean Temp °C", justify="right")
    table.add_column("Total Readings", justify="right")

    for row in top.iter_rows():
        table.add_row(str(row[0]), str(row[1]), str(row[2]))

    console.print(table)


if __name__ == "__main__":
    main()
