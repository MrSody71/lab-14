# Prompt Log — Weather Pipeline

Лабораторная работа №14, вариант 2.
Каждая запись соответствует одному атомарному коммиту.

---

## 00-1 · Корневые файлы

**Файл:** `prompts/00-1-root-files.md`
**Коммит:** `4bc9a54 chore: add root files (README, gitignore, license, env example)`

Созданы корневые файлы репозитория:
- `README.md` — скелет с разделами и таблицей технологического стека
- `.gitignore` — шаблоны GitHub для Go, Python, Rust, IDE, OS + кастомные правила
- `.editorconfig` — единый стиль для всех языков
- `LICENSE` — MIT 2025, Weather Pipeline Authors
- `.env.example` — переменные окружения (OWM mock, Kafka, NATS, etcd, Arrow Flight)
- `CONTRIBUTING.md` — правило обязательного prompts/NN-<topic>.md в каждом PR

---

## 00-2 · Структура каталогов

**Файл:** `prompts/00-2-directories.md`
**Коммит:** `e74862d chore: create directory layout with .gitkeep placeholders`

Создана полная структура каталогов с `.gitkeep`-заглушками:
- `go-collector/` — cmd, internal (api, shard, window, sink, metrics, config), pkg
- `arrow-server/` — cmd, internal
- `mock-owm/` — cmd, internal
- `rust-validator/` — src, tests
- `py-analyzer/` — src/analyzer, tests, notebooks
- `py-asyncio-collector/` — src
- `dashboard/`
- `k8s/` — base, overlays/dev, overlays/prod
- `bench/` — scenarios, results, plots
- `docs/` — screenshots, diagrams
- `prompts/`

---

## 00-3 · Go workspace

**Файл:** `prompts/00-3-go-workspace.md`
**Коммит:** `08ee77e chore(go): set up go workspace with three module stubs`

Создан Go workspace и три модуля-заглушки:
- `go.work` — workspace, объединяет go-collector, arrow-server, mock-owm
- `go-collector/go.mod` — `github.com/MrSody71/weather-pipeline/go-collector`
- `arrow-server/go.mod` — `github.com/MrSody71/weather-pipeline/arrow-server`
- `mock-owm/go.mod` — `github.com/MrSody71/weather-pipeline/mock-owm`
- Три `cmd/.../main.go` заглушки (печатают `v0.0.0 starting` и завершаются с кодом 0)
- `.golangci.yml` — линтеры: govet, staticcheck, errcheck, revive, gocyclo, unused, ineffassign, gosec

---

## 00-4 · Rust crate заглушка

**Файл:** `prompts/00-4-rust-stub.md`
**Коммит:** `ab4a414 chore(rust): scaffold rust-validator crate with PyO3 stub`

Создан Rust crate `rust-validator` с PyO3:
- `Cargo.toml` — pyo3 0.22, features: extension-module + abi3-py311, crate-type: [cdylib, rlib]
- `src/lib.rs` — заглушка `validate_dummy() -> bool`, PyModule, unit-тест
- `tests/smoke.rs` — интеграционный smoke-тест (проверяет, что crate линкуется)
- `.gitignore` — исключает `target/` и `Cargo.lock`

---

## 00-5 · Python-проекты

**Файл:** `prompts/00-5-python-projects.md`
**Коммит:** `41cf063 chore(py): scaffold three python projects with uv`

Созданы три Python-проекта с src-layout и управлением через `uv`:

| Проект | Пакет | Ключевые зависимости |
| --- | --- | --- |
| `py-analyzer` | `analyzer` | polars, duckdb, pyarrow, kafka-python, nats-py, plotly, pydantic, typer |
| `py-asyncio-collector` | `collector` | aiohttp, httpx, rich, typer, pydantic |
| `dashboard` | `dashboard` | streamlit, plotly, pyarrow, polars, kafka-python, nats-py, pydantic |

Каждый проект: `pyproject.toml` (hatchling build), `src/<pkg>/__init__.py`, `tests/test_smoke.py`, ruff + pytest конфиг.

---

## 00-6 · docker-compose.yml и Makefile

**Файл:** `prompts/00-6-compose-makefile.md`
**Коммит:** `dabb094 chore: add docker-compose infra and Makefile`

Создана инфраструктура для локальной разработки:

`docker-compose.yml` — только инфраструктурные сервисы:
- `redpanda` v24.2.7 — Kafka API брокер, healthcheck через `rpk cluster health`
- `redpanda-console` v2.7.2 — веб-UI на порту 8080
- `nats` 2.10-alpine — JetStream включён (`-js`), monitoring на 8222
- `etcd` v3.5.15 — одна нода, healthcheck через `etcdctl endpoint health`
- Сеть `weather-net` (bridge)

`Makefile` — цели: help, bootstrap, build-go, build-rust, build, test-go, test-rust, test-py, test, lint-go, lint-rust, lint-py, lint, fmt, docker-up, docker-down, docker-logs, k8s-up (заглушка), k8s-down (заглушка), clean.

---

## 00-7 · GitHub Actions CI

**Файл:** `prompts/00-7-ci.md`
**Коммит:** `0e48773 ci: add github actions workflows`

Созданы два workflow-файла:

`.github/workflows/ci.yml` — четыре job:
- `go` — setup-go 1.22, go work sync, build ×3, test -race ×3, golangci-lint v1.61.0
- `python` — matrix [py-analyzer, py-asyncio-collector, dashboard]: setup-uv, uv sync, ruff check, pytest
- `rust` — dtolnay/rust-toolchain stable, Swatinem/rust-cache, fmt --check, clippy -D warnings, test, build --release
- `prompts-gate` — проверяет наличие prompts/*.md и сканирует на утечку секретов (OWM_API_KEY, sk-*, ghp_*)

`.github/workflows/codeql.yml` — CodeQL анализ Go и Python:
- Триггеры: push/PR на main + расписание (понедельник 06:00 UTC)
- permissions: security-events: write
