"""
Асинхронный HTTP-клиент для опроса мок OWM.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime

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
    error: str | None = None

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
