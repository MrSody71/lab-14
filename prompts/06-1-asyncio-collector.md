Реализуй коллектор на Python asyncio/aiohttp —
функциональный аналог Go-коллектора для сравнения производительности.
Тот же мок OWM, те же города, тот же интервал — но на Python.

=== py-asyncio-collector/src/collector/config.py ===

"""Конфигурация asyncio-коллектора."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    mock_owm_url: str
    cities: list[str]
    poll_interval_sec: float
    concurrency: int        # макс. одновременных запросов
    total_requests: int     # сколько запросов сделать (для бенча)
    output_file: str        # куда писать JSONL

    @classmethod
    def load(cls) -> "Config":
        return cls(
            mock_owm_url=os.getenv(
                "OWM_MOCK_URL", "http://localhost:8081"
            ),
            cities=os.getenv(
                "CITIES",
                "Moscow,Saint-Petersburg,Novosibirsk,"
                "Yekaterinburg,Kazan,Stockholm,"
                "Berlin,London,New-York,Tokyo",
            ).split(","),
            poll_interval_sec=float(
                os.getenv("POLL_INTERVAL_SEC", "10")
            ),
            concurrency=int(os.getenv("CONCURRENCY", "10")),
            total_requests=int(
                os.getenv("TOTAL_REQUESTS", "100")
            ),
            output_file=os.getenv(
                "OUTPUT_FILE", "data/py_collector_output.jsonl"
            ),
        )

=== py-asyncio-collector/src/collector/fetcher.py ===

"""
Асинхронный HTTP-клиент для опроса мок OWM.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class WeatherReading:
    city: str
    country: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    description: str
    collected_at: str   # ISO datetime
    response_time_ms: float
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


async def fetch_city(
    session: aiohttp.ClientSession,
    base_url: str,
    city: str,
    semaphore: asyncio.Semaphore,
) -> WeatherReading:
    """
    Делает один HTTP-запрос к мок OWM для города.
    Семафор ограничивает параллелизм.
    Всегда возвращает WeatherReading — с данными или с error.
    """
    url = f"{base_url}/data/2.5/weather?q={city}&units=metric"
    t0 = time.perf_counter()

    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(
                total=10
            )) as resp:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                if resp.status == 200:
                    data = await resp.json()
                    return WeatherReading(
                        city=data.get("name", city),
                        country=data.get("sys", {}).get("country", ""),
                        temperature=data.get("main", {}).get("temp", 0),
                        feels_like=data.get("main", {}).get(
                            "feels_like", 0
                        ),
                        humidity=data.get("main", {}).get("humidity", 0),
                        pressure=data.get("main", {}).get("pressure", 0),
                        wind_speed=data.get("wind", {}).get("speed", 0),
                        description=(
                            data.get("weather", [{}])[0]
                            .get("description", "")
                        ),
                        collected_at=datetime.utcnow().isoformat(),
                        response_time_ms=round(elapsed_ms, 2),
                    )
                else:
                    return WeatherReading(
                        city=city, country="", temperature=0,
                        feels_like=0, humidity=0, pressure=0,
                        wind_speed=0, description="",
                        collected_at=datetime.utcnow().isoformat(),
                        response_time_ms=round(elapsed_ms, 2),
                        error=f"HTTP {resp.status}",
                    )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return WeatherReading(
                city=city, country="", temperature=0,
                feels_like=0, humidity=0, pressure=0,
                wind_speed=0, description="",
                collected_at=datetime.utcnow().isoformat(),
                response_time_ms=round(elapsed_ms, 2),
                error=str(e),
            )


async def fetch_all_cities(
    base_url: str,
    cities: list[str],
    concurrency: int = 10,
) -> list[WeatherReading]:
    """
    Параллельно опрашивает все города.
    Возвращает список WeatherReading (успешных и нет).
    """
    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_city(session, base_url, city, semaphore)
            for city in cities
        ]
        results = await asyncio.gather(*tasks)

    return list(results)

=== py-asyncio-collector/src/collector/__main__.py ===

"""
Точка входа: python -m collector
"""
from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from pathlib import Path

from collector.config import Config
from collector.fetcher import fetch_all_cities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def run_once(cfg: Config) -> dict:
    """
    Один раунд: опросить все города, вернуть статистику.
    """
    t0 = time.perf_counter()
    readings = await fetch_all_cities(
        cfg.mock_owm_url, cfg.cities, cfg.concurrency
    )
    elapsed = (time.perf_counter() - t0) * 1000

    ok = [r for r in readings if r.error is None]
    err = [r for r in readings if r.error is not None]

    return {
        "total": len(readings),
        "success": len(ok),
        "errors": len(err),
        "elapsed_ms": round(elapsed, 2),
        "avg_response_ms": round(
            sum(r.response_time_ms for r in ok) / len(ok), 2
        ) if ok else 0,
        "readings": [r.to_dict() for r in readings],
    }


async def main() -> None:
    cfg = Config.load()
    stop = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_event_loop().add_signal_handler(
                sig, stop.set
            )
        except NotImplementedError:
            pass

    output = Path(cfg.output_file)
    output.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Starting asyncio collector: %d cities, "
        "concurrency=%d",
        len(cfg.cities), cfg.concurrency,
    )

    rounds = 0
    with open(output, "w") as f:
        while not stop.is_set():
            stats = await run_once(cfg)
            rounds += 1

            # Записываем каждое показание в JSONL
            for r in stats["readings"]:
                f.write(json.dumps(r) + "\n")
            f.flush()

            logger.info(
                "Round %d: %d/%d ok, %.1fms total, "
                "%.1fms avg response",
                rounds,
                stats["success"], stats["total"],
                stats["elapsed_ms"],
                stats["avg_response_ms"],
            )

            try:
                await asyncio.wait_for(
                    stop.wait(),
                    timeout=cfg.poll_interval_sec,
                )
            except asyncio.TimeoutError:
                pass

    logger.info("Collector stopped. Rounds: %d", rounds)


if __name__ == "__main__":
    asyncio.run(main())

=== py-asyncio-collector/tests/test_fetcher.py ===

"""Tests for asyncio fetcher — uses aiohttp test server."""
import asyncio
import json
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from collector.fetcher import fetch_city, fetch_all_cities
import aiohttp


def make_owm_response(city: str) -> dict:
    return {
        "id": 524901,
        "name": city,
        "dt": 1700000000,
        "main": {
            "temp": 15.0, "feels_like": 13.0,
            "temp_min": 12.0, "temp_max": 18.0,
            "pressure": 1013, "humidity": 65,
        },
        "wind": {"speed": 5.0, "deg": 180},
        "clouds": {"all": 40},
        "weather": [{"description": "few clouds", "icon": "02d"}],
        "coord": {"lat": 55.75, "lon": 37.62},
        "sys": {"country": "RU"},
    }


@pytest.fixture()
def mock_owm_app():
    """aiohttp приложение — мок OWM."""
    async def weather_handler(request: web.Request) -> web.Response:
        city = request.rel_url.query.get("q", "Unknown")
        if city == "Atlantis":
            return web.Response(
                status=404,
                content_type="application/json",
                body=json.dumps(
                    {"cod": "404", "message": "city not found"}
                ),
            )
        return web.Response(
            content_type="application/json",
            body=json.dumps(make_owm_response(city)),
        )

    async def slow_handler(request: web.Request) -> web.Response:
        await asyncio.sleep(0.5)
        city = request.rel_url.query.get("q", "Unknown")
        return web.Response(
            content_type="application/json",
            body=json.dumps(make_owm_response(city)),
        )

    app = web.Application()
    app.router.add_get(
        "/data/2.5/weather", weather_handler
    )
    app.router.add_get(
        "/slow/weather", slow_handler
    )
    return app


@pytest.fixture()
async def owm_server(aiohttp_server, mock_owm_app):
    return await aiohttp_server(mock_owm_app)


@pytest.mark.asyncio
async def test_fetch_city_success(owm_server):
    base = str(owm_server.make_url(""))
    semaphore = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as session:
        reading = await fetch_city(
            session, base, "Moscow", semaphore
        )
    assert reading.error is None
    assert reading.city == "Moscow"
    assert reading.temperature == 15.0
    assert reading.humidity == 65
    assert reading.response_time_ms > 0


@pytest.mark.asyncio
async def test_fetch_city_404(owm_server):
    base = str(owm_server.make_url(""))
    semaphore = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as session:
        reading = await fetch_city(
            session, base, "Atlantis", semaphore
        )
    assert reading.error is not None
    assert "404" in reading.error


@pytest.mark.asyncio
async def test_fetch_all_cities(owm_server):
    base = str(owm_server.make_url(""))
    cities = ["Moscow", "London", "Tokyo"]
    results = await fetch_all_cities(base, cities, concurrency=3)
    assert len(results) == 3
    ok = [r for r in results if r.error is None]
    assert len(ok) == 3


@pytest.mark.asyncio
async def test_fetch_concurrency(owm_server):
    """
    Параллельные запросы должны быть быстрее последовательных.
    10 запросов с concurrency=10 должны занять ~время одного.
    """
    base = str(owm_server.make_url(""))
    cities = ["Moscow"] * 5
    import time
    t0 = time.perf_counter()
    results = await fetch_all_cities(base, cities, concurrency=5)
    elapsed = time.perf_counter() - t0
    # 5 параллельных быстрых запросов должны занять < 1 сек
    assert elapsed < 1.0
    assert len(results) == 5

Добавь в py-asyncio-collector/pyproject.toml:
  dependencies = [
    "aiohttp>=3.9",
    "httpx",
    "rich",
    "typer",
    "pydantic",
  ]
  [dependency-groups]
  dev = [
    "pytest",
    "pytest-asyncio",
    "pytest-aiohttp",
    "ruff",
    "mypy",
  ]

  [tool.pytest.ini_options]
  asyncio_mode = "auto"

ПРОВЕРКА:
  cd py-asyncio-collector
  uv sync 2>&1
  uv run pytest tests/ -v 2>&1
  cd ..

4 теста зелёных.

prompts/06-1-asyncio-collector.md — этот промт целиком.
