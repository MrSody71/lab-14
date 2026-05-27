Создай скрипт для генерации графиков по результатам бенчмарка.
Он читает JSON из bench/results/ и рисует сравнительные диаграммы.

=== bench/scenarios/plot_bench.py ===

"""
Генерация графиков по результатам бенчмарка.

Запуск:
  python bench/scenarios/plot_bench.py              # последний файл
  python bench/scenarios/plot_bench.py results.json # конкретный файл
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

RESULTS_DIR = Path(__file__).parent.parent / "results"
PLOTS_DIR   = Path(__file__).parent.parent / "plots"
COLORS = {
    "go":             "#00ADD8",   # Go blue
    "python-asyncio": "#FFD43B",   # Python yellow
}


def load_latest() -> dict:
    """Загружает самый свежий файл из bench/results/."""
    files = sorted(RESULTS_DIR.glob("bench_*.json"))
    if not files:
        raise FileNotFoundError(
            f"No bench results in {RESULTS_DIR}. "
            "Run run_bench.py first."
        )
    return json.loads(files[-1].read_text())


def load_file(path: Path) -> dict:
    return json.loads(path.read_text())


# ── График 1: Throughput (req/s) ─────────────────────────────────────────

def plot_throughput(data: dict, out_dir: Path) -> Path:
    results = data["results"]
    names = [r["name"] for r in results]
    values = [r["throughput_rps"] for r in results]
    colors = [COLORS.get(n, "#888") for n in names]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, values, color=colors,
                  edgecolor="white", linewidth=1.5)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.01,
            f"{val:.1f}", ha="center", va="bottom",
            fontweight="bold", fontsize=11,
        )

    ax.set_title("Throughput: Requests per Second", fontsize=14)
    ax.set_ylabel("req/s", fontsize=12)
    ax.set_ylim(0, max(values) * 1.2)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    # Аннотация с кратностью
    if len(values) == 2 and min(values) > 0:
        ratio = max(values) / min(values)
        winner = names[values.index(max(values))]
        ax.annotate(
            f"{winner} is {ratio:.1f}× faster",
            xy=(0.5, 0.92), xycoords="axes fraction",
            ha="center", fontsize=10,
            color="#333",
            bbox=dict(boxstyle="round,pad=0.3",
                      facecolor="#f0f0f0", alpha=0.8),
        )

    plt.tight_layout()
    path = out_dir / "throughput.png"
    fig.savefig(str(path), dpi=150)
    plt.close(fig)
    return path


# ── График 2: Latency percentiles ────────────────────────────────────────

def plot_latency(data: dict, out_dir: Path) -> Path:
    results = data["results"]
    # Только Python — у Go нет per-request latency из subprocess
    py_results = [r for r in results
                  if r["avg_latency_ms"] > 0]

    if not py_results:
        print("[WARN] No latency data to plot")
        # Создаём пустой placeholder
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, "No latency data\n(Go binary not available)",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=12, color="#888")
        ax.set_title("Latency Percentiles", fontsize=14)
        path = out_dir / "latency_percentiles.png"
        fig.savefig(str(path), dpi=150)
        plt.close(fig)
        return path

    percentile_labels = ["P50", "P95", "P99", "Max"]
    x = np.arange(len(percentile_labels))
    width = 0.6 / len(py_results)

    fig, ax = plt.subplots(figsize=(9, 5))

    for i, r in enumerate(py_results):
        values = [
            r["p50_latency_ms"],
            r["p95_latency_ms"],
            r["p99_latency_ms"],
            r["max_latency_ms"],
        ]
        offset = (i - len(py_results) / 2 + 0.5) * width
        color = COLORS.get(r["name"], "#888")
        bars = ax.bar(x + offset, values, width * 0.9,
                      label=r["name"], color=color,
                      edgecolor="white", alpha=0.85)
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    f"{val:.1f}", ha="center", va="bottom",
                    fontsize=8,
                )

    ax.set_xticks(x)
    ax.set_xticklabels(percentile_labels)
    ax.set_title("Latency Percentiles (ms)", fontsize=14)
    ax.set_ylabel("Latency (ms)", fontsize=12)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    path = out_dir / "latency_percentiles.png"
    fig.savefig(str(path), dpi=150)
    plt.close(fig)
    return path


# ── График 3: Success rate ────────────────────────────────────────────────

def plot_success_rate(data: dict, out_dir: Path) -> Path:
    results = data["results"]

    fig, axes = plt.subplots(
        1, len(results),
        figsize=(4 * len(results), 4)
    )
    if len(results) == 1:
        axes = [axes]

    for ax, r in zip(axes, results):
        ok = r["successful"]
        fail = r["failed"]
        total = ok + fail
        if total == 0:
            continue
        wedges, texts, autotexts = ax.pie(
            [ok, fail] if fail > 0 else [ok],
            labels=(["Success", "Failed"]
                    if fail > 0 else ["Success"]),
            colors=(["#4CAF50", "#F44336"]
                    if fail > 0 else ["#4CAF50"]),
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        ax.set_title(
            f"{r['name']}\n"
            f"{total:,} total requests",
            fontsize=11,
        )

    plt.suptitle("Request Success Rate", fontsize=14,
                 fontweight="bold")
    plt.tight_layout()
    path = out_dir / "success_rate.png"
    fig.savefig(str(path), dpi=150)
    plt.close(fig)
    return path


# ── График 4: Summary card ────────────────────────────────────────────────

def plot_summary_card(data: dict, out_dir: Path) -> Path:
    """Сводная карточка с ключевыми метриками в виде таблицы."""
    results = data["results"]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis("off")

    headers = [
        "Metric", *[r["name"] for r in results]
    ]
    rows = [
        ["Total requests",
         *[f"{r['total_requests']:,}" for r in results]],
        ["Successful",
         *[f"{r['successful']:,}" for r in results]],
        ["Total time (s)",
         *[f"{r['total_time_sec']:.2f}" for r in results]],
        ["Throughput (req/s)",
         *[f"{r['throughput_rps']:.1f}" for r in results]],
        ["Avg latency (ms)",
         *[f"{r['avg_latency_ms']:.2f}" if r['avg_latency_ms'] > 0
           else "N/A" for r in results]],
        ["P95 latency (ms)",
         *[f"{r['p95_latency_ms']:.2f}" if r['p95_latency_ms'] > 0
           else "N/A" for r in results]],
    ]

    col_colors = ["#E3F2FD"] + [
        [COLORS.get(r["name"], "#eee")] * len(rows[0])
        for r in results
    ][0:1]
    # Упрощённая цветовая схема для таблицы
    cell_colors = [
        ["#E3F2FD"] * len(headers)
        for _ in rows
    ]

    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc="center",
        loc="center",
        cellColours=cell_colors,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)

    # Стилизация заголовка
    for j in range(len(headers)):
        table[0, j].set_facecolor("#1565C0")
        table[0, j].set_text_props(color="white",
                                    fontweight="bold")

    ax.set_title(
        f"Go vs Python Asyncio — Benchmark Summary\n"
        f"Platform: {data.get('platform','unknown')} | "
        f"Cities: {data.get('cities_count', '?')}",
        fontsize=12, pad=20,
    )

    plt.tight_layout()
    path = out_dir / "summary_card.png"
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Main ──────────────────────────────────────────────────────────────────

def plot_results(source: Path | None = None) -> list[Path]:
    """Генерирует все графики, возвращает пути к файлам."""
    if source is None:
        data = load_latest()
    else:
        data = load_file(Path(source))

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    paths = [
        plot_throughput(data, PLOTS_DIR),
        plot_latency(data, PLOTS_DIR),
        plot_success_rate(data, PLOTS_DIR),
        plot_summary_card(data, PLOTS_DIR),
    ]

    print(f"Generated {len(paths)} plots in {PLOTS_DIR}:")
    for p in paths:
        print(f"  {p}")
    return paths


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    plot_results(source)

=== bench/scenarios/test_bench_plots.py ===

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

Создай bench/__init__.py и bench/scenarios/__init__.py (пустые).

ПРОВЕРКА:
  cd py-asyncio-collector
  uv run pytest ../bench/scenarios/test_bench_plots.py -v 2>&1
  cd ..

5 тестов зелёных.

prompts/06-3-bench-plots.md — этот промт целиком.
