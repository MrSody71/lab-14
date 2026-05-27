"""Tests for asyncio fetcher — uses aiohttp test server."""
import asyncio
import json
import pytest
from aiohttp import web

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
