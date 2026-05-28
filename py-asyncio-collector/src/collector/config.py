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
    def load(cls) -> Config:
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
