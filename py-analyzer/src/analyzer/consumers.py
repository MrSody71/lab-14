"""
Kafka и NATS консьюмеры для weather pipeline.
Оба читают WindowAggregate JSON и кладут в asyncio.Queue.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WindowAggregate:
    """Агрегат за одно tumbling-window окно."""
    city: str
    window_start: datetime
    window_end: datetime
    count: int
    avg_temp: float
    min_temp: float
    max_temp: float
    avg_humidity: float
    avg_pressure: float
    avg_wind_speed: float
    shard_id: str

    @classmethod
    def from_dict(cls, d: dict) -> WindowAggregate:
        def parse_dt(v: str | int | float) -> datetime:
            if isinstance(v, (int, float)):
                return datetime.utcfromtimestamp(v)
            return datetime.fromisoformat(
                str(v).replace("Z", "+00:00")
            )
        return cls(
            city=d.get("city", ""),
            window_start=parse_dt(d.get("window_start", 0)),
            window_end=parse_dt(d.get("window_end", 0)),
            count=int(d.get("count", 0)),
            avg_temp=float(d.get("avg_temp", 0)),
            min_temp=float(d.get("min_temp", 0)),
            max_temp=float(d.get("max_temp", 0)),
            avg_humidity=float(d.get("avg_humidity", 0)),
            avg_pressure=float(d.get("avg_pressure", 0)),
            avg_wind_speed=float(d.get("avg_wind_speed", 0)),
            shard_id=d.get("shard_id", ""),
        )

    def to_dict(self) -> dict:
        return {
            "city": self.city,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "count": self.count,
            "avg_temp": self.avg_temp,
            "min_temp": self.min_temp,
            "max_temp": self.max_temp,
            "avg_humidity": self.avg_humidity,
            "avg_pressure": self.avg_pressure,
            "avg_wind_speed": self.avg_wind_speed,
            "shard_id": self.shard_id,
        }


# ── Kafka консьюмер ───────────────────────────────────────────────────────

async def kafka_consumer(
    brokers: list[str],
    topic: str,
    group_id: str,
    queue: asyncio.Queue[WindowAggregate],
    stop_event: asyncio.Event,
) -> None:
    """
    Читает сообщения из Kafka-топика в фоне.
    При ошибке подключения — ждёт 5 сек и пробует снова.
    Останавливается когда stop_event установлен.
    """
    try:
        from kafka import KafkaConsumer as _KC  # noqa: N814
    except ImportError:
        logger.error("kafka-python not installed")
        return

    loop = asyncio.get_event_loop()

    while not stop_event.is_set():
        consumer = None
        try:
            consumer = _KC(
                topic,
                bootstrap_servers=brokers,
                group_id=group_id,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda b: json.loads(b.decode()),
                consumer_timeout_ms=1000,
            )
            logger.info("Kafka consumer connected to %s topic=%s", brokers, topic)

            while not stop_event.is_set():
                msgs = await loop.run_in_executor(None, _poll_kafka, consumer)
                for msg in msgs:
                    try:
                        agg = WindowAggregate.from_dict(msg)
                        await queue.put(agg)
                    except Exception as e:
                        logger.warning("Bad kafka message: %s", e)

        except Exception as e:
            logger.warning("Kafka consumer error: %s. Retry in 5s", e)
            if consumer is not None:
                with contextlib.suppress(Exception):
                    consumer.close()
            await asyncio.sleep(5)


def _poll_kafka(consumer) -> list[dict]:
    """Синхронный poll — запускается в executor."""
    results = []
    try:
        for msg in consumer:
            results.append(msg.value)
            if len(results) >= 50:
                break
    except Exception:
        pass
    return results


# ── NATS консьюмер ────────────────────────────────────────────────────────

async def nats_consumer(
    url: str,
    subject: str,
    queue: asyncio.Queue[WindowAggregate],
    stop_event: asyncio.Event,
) -> None:
    """
    Читает сообщения из NATS JetStream.
    При ошибке подключения — ждёт 5 сек и пробует снова.
    """
    try:
        import nats as _nats
    except ImportError:
        logger.error("nats-py not installed")
        return

    while not stop_event.is_set():
        nc = None
        try:
            nc = await _nats.connect(url)
            js = nc.jetstream()

            sub = await js.subscribe(
                f"{subject}.>",
                durable="py-analyzer",
                deliver_policy="last_per_subject",
            )
            logger.info("NATS consumer connected to %s subject=%s", url, subject)

            while not stop_event.is_set():
                try:
                    msg = await asyncio.wait_for(sub.next_msg(), timeout=1.0)
                    await msg.ack()
                    data = json.loads(msg.data.decode())
                    agg = WindowAggregate.from_dict(data)
                    await queue.put(agg)
                except TimeoutError:
                    continue
                except Exception as e:
                    logger.warning("NATS message error: %s", e)

        except Exception as e:
            logger.warning("NATS consumer error: %s. Retry in 5s", e)
            if nc is not None:
                with contextlib.suppress(Exception):
                    await nc.close()
            await asyncio.sleep(5)


# ── Mock-генератор для тестирования без брокеров ─────────────────────────

async def mock_consumer(
    cities: list[str],
    queue: asyncio.Queue[WindowAggregate],
    stop_event: asyncio.Event,
    interval_sec: float = 2.0,
) -> None:
    """
    Генерирует случайные агрегаты — для тестирования дашборда
    без запущенного коллектора.
    """
    import random
    from datetime import timedelta

    while not stop_event.is_set():
        for city in cities:
            base_temp = random.uniform(-5, 30)
            now = datetime.utcnow()
            agg = WindowAggregate(
                city=city,
                window_start=now - timedelta(seconds=60),
                window_end=now,
                count=random.randint(3, 12),
                avg_temp=round(base_temp, 2),
                min_temp=round(base_temp - random.uniform(0, 3), 2),
                max_temp=round(base_temp + random.uniform(0, 3), 2),
                avg_humidity=round(random.uniform(40, 90), 1),
                avg_pressure=round(random.uniform(1000, 1025), 1),
                avg_wind_speed=round(random.uniform(0, 15), 1),
                shard_id="mock",
            )
            await queue.put(agg)
        await asyncio.sleep(interval_sec)
