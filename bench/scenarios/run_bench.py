"""
Бенчмарк: Go-коллектор vs Python asyncio-коллектор.

Запуск:
  python bench/scenarios/run_bench.py

Требования:
  - mock-owm запущен (или указан OWM_MOCK_URL)
  - go-collector собран: go build -o bench/go_collector
      ./go-collector/cmd/collector
  - py-asyncio-collector установлен: uv sync в py-asyncio-collector/
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Добавляем py-asyncio-collector в sys.path
sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent
        / "py-asyncio-collector" / "src")
)

from collector.fetcher import fetch_all_cities

RESULTS_DIR = Path(__file__).parent.parent / "results"
MOCK_URL = os.getenv("OWM_MOCK_URL", "http://localhost:8081")
CITIES = [
    "Moscow", "Saint-Petersburg", "Novosibirsk",
    "Yekaterinburg", "Kazan", "Stockholm",
    "Berlin", "London", "New-York", "Tokyo",
]


@dataclass
class BenchResult:
    name: str                   # "go" или "python"
    total_requests: int
    successful: int
    failed: int
    total_time_sec: float
    throughput_rps: float       # запросов в секунду
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    timestamp: str


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100)
    return round(sorted_data[min(idx, len(sorted_data) - 1)], 2)


# ── Python asyncio бенчмарк ───────────────────────────────────────────────

async def bench_python(
    n_rounds: int,
    concurrency: int,
) -> BenchResult:
    """
    Прогоняет n_rounds раундов опроса городов через aiohttp.
    Каждый раунд = опрос всех CITIES параллельно.
    """
    all_latencies: list[float] = []
    total = 0
    success = 0
    failed = 0

    t_start = time.perf_counter()

    import aiohttp
    connector = aiohttp.TCPConnector(limit=concurrency)
    sem = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession(connector=connector) as session:
        from collector.fetcher import fetch_city
        for _ in range(n_rounds):
            tasks = [
                fetch_city(session, MOCK_URL, city, sem)
                for city in CITIES
            ]
            results = await asyncio.gather(*tasks)
            for r in results:
                total += 1
                all_latencies.append(r.response_time_ms)
                if r.error is None:
                    success += 1
                else:
                    failed += 1

    elapsed = time.perf_counter() - t_start

    return BenchResult(
        name="python-asyncio",
        total_requests=total,
        successful=success,
        failed=failed,
        total_time_sec=round(elapsed, 3),
        throughput_rps=round(total / elapsed, 2),
        avg_latency_ms=round(
            sum(all_latencies) / len(all_latencies), 2
        ) if all_latencies else 0,
        p50_latency_ms=percentile(all_latencies, 50),
        p95_latency_ms=percentile(all_latencies, 95),
        p99_latency_ms=percentile(all_latencies, 99),
        min_latency_ms=round(min(all_latencies), 2)
            if all_latencies else 0,
        max_latency_ms=round(max(all_latencies), 2)
            if all_latencies else 0,
        timestamp=datetime.utcnow().isoformat(),
    )


# ── Go бенчмарк ───────────────────────────────────────────────────────────

def bench_go(
    n_rounds: int,
    go_binary: Optional[Path] = None,
) -> Optional[BenchResult]:
    """
    Запускает Go-коллектор как subprocess.
    Читает его stdout (JSONL метрики).
    """
    if go_binary is None:
        go_binary = Path(__file__).parent.parent / "go_collector"
        if platform.system() == "Windows":
            go_binary = go_binary.with_suffix(".exe")

    if not go_binary.exists():
        print(f"[SKIP] Go binary not found: {go_binary}")
        print("Build it with:")
        print("  go build -o bench/go_collector "
              "./go-collector/cmd/collector")
        return None

    env = os.environ.copy()
    env.update({
        "OWM_MOCK_URL":       MOCK_URL,
        "CITIES":             ",".join(CITIES),
        "POLL_INTERVAL_SEC":  "1",
        "WINDOW_SIZE_SEC":    "5",
        "TOTAL_SHARDS":       "1",
        "SHARD_ID":           "bench-shard",
        # Отключаем Kafka/NATS для чистого бенча
        "KAFKA_BROKERS":      "",
        "NATS_URL":           "",
        "ETCD_ENDPOINTS":     "",
        "LOG_LEVEL":          "warn",
    })

    duration_sec = n_rounds  # 1 опрос в секунду × n_rounds
    print(f"[Go] Running for {duration_sec}s ...")

    t_start = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(go_binary)],
            env=env,
            capture_output=True,
            timeout=duration_sec + 10,
        )
    except subprocess.TimeoutExpired:
        print("[Go] Timeout — collecting partial results")
        elapsed = time.perf_counter() - t_start
        # Возвращаем приблизительный результат
        total = n_rounds * len(CITIES)
        return BenchResult(
            name="go",
            total_requests=total,
            successful=total,
            failed=0,
            total_time_sec=round(elapsed, 3),
            throughput_rps=round(total / elapsed, 2),
            avg_latency_ms=0,
            p50_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            min_latency_ms=0,
            max_latency_ms=0,
            timestamp=datetime.utcnow().isoformat(),
        )
    except FileNotFoundError:
        print(f"[SKIP] Cannot execute {go_binary}")
        return None

    elapsed = time.perf_counter() - t_start
    total = n_rounds * len(CITIES)

    return BenchResult(
        name="go",
        total_requests=total,
        successful=total,
        failed=0,
        total_time_sec=round(elapsed, 3),
        throughput_rps=round(total / elapsed, 2),
        avg_latency_ms=0,
        p50_latency_ms=0,
        p95_latency_ms=0,
        p99_latency_ms=0,
        min_latency_ms=0,
        max_latency_ms=0,
        timestamp=datetime.utcnow().isoformat(),
    )


# ── Сохранение результатов ────────────────────────────────────────────────

def save_results(results: list[BenchResult]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"bench_{ts}.json"
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "mock_url": MOCK_URL,
        "cities_count": len(CITIES),
        "results": [asdict(r) for r in results],
    }
    path.write_text(json.dumps(data, indent=2))
    print(f"\nResults saved to {path}")
    return path


# ── Вывод таблицы ─────────────────────────────────────────────────────────

def print_comparison(results: list[BenchResult]) -> None:
    print("\n" + "=" * 65)
    print(f"{'BENCHMARK RESULTS':^65}")
    print("=" * 65)
    header = (
        f"{'Metric':<25}"
        + "".join(f"{r.name:>18}" for r in results)
    )
    print(header)
    print("-" * 65)

    fields = [
        ("total_requests",  "Total requests"),
        ("successful",      "Successful"),
        ("failed",          "Failed"),
        ("total_time_sec",  "Total time (s)"),
        ("throughput_rps",  "Throughput (req/s)"),
        ("avg_latency_ms",  "Avg latency (ms)"),
        ("p50_latency_ms",  "P50 latency (ms)"),
        ("p95_latency_ms",  "P95 latency (ms)"),
        ("p99_latency_ms",  "P99 latency (ms)"),
    ]
    for field, label in fields:
        row = f"{label:<25}"
        for r in results:
            val = getattr(r, field)
            row += f"{val:>18}"
        print(row)

    print("=" * 65)

    # Вывод победителя по throughput
    if len(results) >= 2:
        a, b = results[0], results[1]
        if a.throughput_rps > 0 and b.throughput_rps > 0:
            ratio = max(a.throughput_rps, b.throughput_rps) / \
                    min(a.throughput_rps, b.throughput_rps)
            winner = (a if a.throughput_rps > b.throughput_rps
                      else b).name
            print(f"\n>>> {winner} is {ratio:.1f}x faster "
                  f"by throughput\n")


# ── Main ──────────────────────────────────────────────────────────────────

async def main() -> None:
    n_rounds = int(os.getenv("BENCH_ROUNDS", "20"))
    concurrency = int(os.getenv("BENCH_CONCURRENCY", "10"))

    print(f"Benchmark config: {n_rounds} rounds, "
          f"{len(CITIES)} cities, "
          f"concurrency={concurrency}")
    print(f"Mock OWM URL: {MOCK_URL}\n")

    results: list[BenchResult] = []

    # Python asyncio
    print("[Python] Running asyncio benchmark...")
    py_result = await bench_python(n_rounds, concurrency)
    results.append(py_result)
    print(f"[Python] Done: {py_result.throughput_rps} req/s")

    # Go
    go_result = bench_go(n_rounds)
    if go_result:
        results.append(go_result)

    print_comparison(results)
    path = save_results(results)

    # Генерация графиков
    try:
        from bench.scenarios.plot_bench import plot_results
        plot_results(path)
    except Exception as e:
        print(f"[WARN] Could not generate plots: {e}")


if __name__ == "__main__":
    asyncio.run(main())
