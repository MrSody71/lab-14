"""Tests for bench plot generation — uses synthetic data."""
import json
import pytest
from pathlib import Path
from bench.scenarios.plot_bench import (
    plot_throughput, plot_latency,
    plot_success_rate, plot_summary_card,
)

SAMPLE_DATA = {
    "timestamp": "2024-01-01T00:00:00",
    "platform": "Linux-test",
    "python_version": "3.11.0",
    "mock_url": "http://localhost:8081",
    "cities_count": 10,
    "results": [
        {
            "name": "python-asyncio",
            "total_requests": 200,
            "successful": 198,
            "failed": 2,
            "total_time_sec": 4.5,
            "throughput_rps": 44.4,
            "avg_latency_ms": 12.3,
            "p50_latency_ms": 11.0,
            "p95_latency_ms": 25.0,
            "p99_latency_ms": 40.0,
            "min_latency_ms": 5.0,
            "max_latency_ms": 55.0,
            "timestamp": "2024-01-01T00:00:00",
        },
        {
            "name": "go",
            "total_requests": 200,
            "successful": 200,
            "failed": 0,
            "total_time_sec": 2.1,
            "throughput_rps": 95.2,
            "avg_latency_ms": 0,
            "p50_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
            "min_latency_ms": 0,
            "max_latency_ms": 0,
            "timestamp": "2024-01-01T00:00:00",
        },
    ],
}


def test_plot_throughput(tmp_path):
    path = plot_throughput(SAMPLE_DATA, tmp_path)
    assert path.exists()
    assert path.stat().st_size > 1000


def test_plot_latency(tmp_path):
    path = plot_latency(SAMPLE_DATA, tmp_path)
    assert path.exists()


def test_plot_success_rate(tmp_path):
    path = plot_success_rate(SAMPLE_DATA, tmp_path)
    assert path.exists()
    assert path.stat().st_size > 1000


def test_plot_summary_card(tmp_path):
    path = plot_summary_card(SAMPLE_DATA, tmp_path)
    assert path.exists()
    assert path.stat().st_size > 1000


def test_all_plots_generated(tmp_path):
    """Все 4 графика создаются без ошибок."""
    paths = [
        plot_throughput(SAMPLE_DATA, tmp_path),
        plot_latency(SAMPLE_DATA, tmp_path),
        plot_success_rate(SAMPLE_DATA, tmp_path),
        plot_summary_card(SAMPLE_DATA, tmp_path),
    ]
    assert all(p.exists() for p in paths)
    assert len(paths) == 4
