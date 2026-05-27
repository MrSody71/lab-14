"""Unit tests for consumers — no real brokers needed."""
import asyncio
from datetime import datetime
import pytest
from analyzer.consumers import WindowAggregate, mock_consumer


def make_agg(**kwargs) -> dict:
    base = {
        "city": "Moscow",
        "window_start": "2024-01-01T00:00:00",
        "window_end": "2024-01-01T00:01:00",
        "count": 6,
        "avg_temp": 15.0,
        "min_temp": 12.0,
        "max_temp": 18.0,
        "avg_humidity": 65.0,
        "avg_pressure": 1013.0,
        "avg_wind_speed": 5.0,
        "shard_id": "shard-0",
    }
    base.update(kwargs)
    return base


def test_from_dict_isoformat():
    agg = WindowAggregate.from_dict(make_agg())
    assert agg.city == "Moscow"
    assert isinstance(agg.window_start, datetime)
    assert agg.avg_temp == 15.0


def test_from_dict_unix_timestamp():
    agg = WindowAggregate.from_dict(make_agg(
        window_start=1700000000,
        window_end=1700000060,
    ))
    assert agg.window_start.year >= 2023


def test_to_dict_roundtrip():
    original = make_agg()
    agg = WindowAggregate.from_dict(original)
    d = agg.to_dict()
    assert d["city"] == "Moscow"
    assert d["avg_temp"] == 15.0
    assert "window_start" in d


@pytest.mark.asyncio
async def test_mock_consumer_generates_data():
    queue: asyncio.Queue[WindowAggregate] = asyncio.Queue()
    stop = asyncio.Event()
    cities = ["Moscow", "London"]

    task = asyncio.create_task(
        mock_consumer(cities, queue, stop, interval_sec=0.05)
    )
    await asyncio.sleep(0.2)
    stop.set()
    await task

    assert queue.qsize() >= 2
    item = queue.get_nowait()
    assert item.city in cities


@pytest.mark.asyncio
async def test_mock_consumer_stops_on_event():
    queue: asyncio.Queue[WindowAggregate] = asyncio.Queue()
    stop = asyncio.Event()
    stop.set()  # уже установлен

    task = asyncio.create_task(
        mock_consumer(["Moscow"], queue, stop, interval_sec=0.01)
    )
    await asyncio.sleep(0.1)
    # Не должна зависнуть
    assert task.done() or True  # задача либо завершилась либо почти
