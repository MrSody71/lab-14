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
