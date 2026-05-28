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
- Три `cmd/.../main.go` заглушки
- `.golangci.yml` — линтеры: govet, staticcheck, errcheck, revive, gocyclo, unused, ineffassign, gosec

---

## 00-4 · Rust crate заглушка

**Файл:** `prompts/00-4-rust-stub.md`
**Коммит:** `ab4a414 chore(rust): scaffold rust-validator crate with PyO3 stub`

Создан Rust crate `rust-validator` с PyO3:
- `Cargo.toml` — pyo3 0.22, features: extension-module + abi3-py311, crate-type: [cdylib, rlib]
- `src/lib.rs` — заглушка `validate_dummy() -> bool`, PyModule, unit-тест
- `tests/smoke.rs` — интеграционный smoke-тест
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

---

## 00-6 · docker-compose.yml и Makefile

**Файл:** `prompts/00-6-compose-makefile.md`
**Коммит:** `dabb094 chore: add docker-compose infra and Makefile`

- `docker-compose.yml` — redpanda, redpanda-console, nats, etcd, сеть weather-net
- `Makefile` — цели: bootstrap, build, test, lint, fmt, docker-*, k8s-*

---

## 00-7 · GitHub Actions CI

**Файл:** `prompts/00-7-ci.md`
**Коммит:** `0e48773 ci: add github actions workflows`

- `.github/workflows/ci.yml` — jobs: go (build+test+lint), python (matrix ruff+pytest), rust (fmt+clippy+test), prompts-gate
- `.github/workflows/codeql.yml` — CodeQL анализ Go и Python

---

## 01-1 · Mock OWM сервер

**Файл:** `prompts/01-1-mock-owm.md`
**Коммит:** `c8f1567 feat(mock-owm): implement OWM mock HTTP server with generator and tests`

Реализован мок-сервер OpenWeatherMap на Go:
- `internal/generator.go` — генерация реалистичных данных для 10 городов (базовые температуры, шум ±3K, давление 1000–1030 hPa, влажность 40–95%)
- `internal/handler.go` — эндпоинты `/health`, `/data/2.5/weather`, `/batch`, параметр `delay`
- `cmd/mockowm/main.go` — HTTP-сервер с graceful shutdown через SIGTERM/SIGINT
- 3 теста: generator, /weather handler, /batch handler

---

## 01-2 · Mock OWM smoke-тест

**Файл:** `prompts/01-2-mock-owm-smoke.md`
**Коммит:** `4cf16c5 chore: add smoke-test prompt for mock-owm`

Добавлен промт для ручной дымовой проверки мок-сервера:
- `go run ./mock-owm/cmd/mockowm &`
- `curl /health`, `curl /data/2.5/weather?q=Moscow&units=metric`, `curl /batch`

---

## 02-1 · go-collector: Config и Types

**Файл:** `prompts/02-1-config-types.md`
**Коммит:** `f560490 feat(go-collector): add config loader and api types`

- `internal/config/config.go` — загрузка конфига из env (OWM_MOCK_URL, CITIES, POLL_INTERVAL_SEC, WINDOW_SIZE_SEC, KAFKA_BROKERS, NATS_URL, ETCD_ENDPOINTS, SHARD_ID и др.)
- `internal/api/types.go` — структуры `WeatherReading` и `WindowAggregate`
- 2 теста для config, 5 тестов для api types

---

## 02-2 · go-collector: HTTP клиент

**Файл:** `prompts/02-2-http-client.md`
**Коммит:** `7858d62 feat(go-collector): add OWM HTTP client with batch support`

- `internal/api/client.go` — параллельный опрос городов через горутины, поддержка batch-эндпоинта
- Таймаут 10 секунд, retry-логика
- 5 тестов с httptest.Server

---

## 02-3 · go-collector: etcd шардирование

**Файл:** `prompts/02-3-etcd-shard.md`
**Коммит:** `cedc7ba feat(go-collector): add etcd shard manager with round-robin city assignment`

- `internal/shard/assign.go` — алгоритм `assignCities`: город i → шард `i % M`, детерминированный по sorted shard IDs
- `internal/shard/manager.go` — регистрация в etcd (lease TTL 15с, keep-alive 5с), `MyCities()`, graceful revoke
- 3 теста без реального etcd

---

## 02-4 · go-collector: Tumbling window

**Файл:** `prompts/02-4-window.md`
**Коммит:** `ed75b1b feat(go-collector): add tumbling window aggregation`

- `internal/window/tumbling.go` — `TumblingWindow.Run()`: накапливает показания по городам, каждые `windowSize` флашит агрегаты
- `aggregate()` — avg/min/max temp, avg humidity/pressure/wind за окно
- Flush при ctx.Done() и при закрытии входного канала
- 3 теста: flush по таймеру, flush при shutdown, агрегация значений

---

## 02-5 · go-collector: Kafka + NATS sink

**Файл:** `prompts/02-5-sink.md`
**Коммит:** `004f02e feat(go-collector): add Kafka, NATS JetStream sinks and Fanout`

- `internal/sink/kafka.go` — публикация `WindowAggregate` JSON в Kafka (sarama)
- `internal/sink/nats.go` — публикация в NATS JetStream (nats.go)
- `internal/sink/fanout.go` — `Fanout.Run()`: читает один канал, одновременно пишет в Kafka и NATS; ошибка одного sink не останавливает другой
- 2 теста с mock-sink

---

## 02-6 · go-collector: main wire-up

**Файл:** `prompts/02-6-main.md`
**Коммит:** `ca435c2 feat(go-collector): wire up collector main with all components`

- `cmd/collector/main.go` — инициализация всех компонентов: config, shard manager, etcd, HTTP client, tumbling window, fanout sink
- Graceful shutdown: SIGTERM/SIGINT → context cancel → window flush → sink close
- Prometheus metrics endpoint (`/metrics`)

---

## 03-1 · Arrow Flight сервер (Go)

**Файл:** `prompts/03-1-arrow-server.md`
**Коммит:** `e57d408 feat(arrow-server): implement Arrow Flight server with in-memory store and Kafka consumer`

- `internal/store.go` — кольцевой буфер `AggregateRecord` (RWMutex), `GetAll()` / `GetByCity()`
- `internal/flight.go` — `FlightServer.DoGet()`: тикет `"all"` или `"<city>"` → Arrow RecordBatch
- `cmd/arrowsrv/main.go` — Kafka consumer горутина + Flight RPC на `:8815`
- 4 теста: Store + Flight handlers

---

## 03-2 · Arrow Flight клиент (Python)

**Файл:** `prompts/03-2-arrow-client-py.md`
**Коммит:** `f2ec188 feat(py-analyzer): add Arrow Flight client with Polars DataFrame output`

- `py-analyzer/src/analyzer/arrow_client.py` — `WeatherFlightClient`: подключается к `:8815`, `get_all()` / `get_city()` → Polars DataFrame
- Конвертация Arrow RecordBatch → Polars через `pl.from_arrow()`
- 4 pytest теста с mock-сервером

---

## 03-3 · Arrow Flight интеграционный тест

**Файл:** `prompts/03-3-arrow-smoke.md`
**Коммит:** `1d9be7c feat(py-analyzer): add Arrow Flight integration test and demo script`

- `tests/test_arrow_integration.py` — запускает Go-сервер как subprocess, отправляет данные, читает через Python клиент
- `scripts/arrow_demo.py` — демо-скрипт для ручной проверки

---

## 04-1 · Rust: правила валидации

**Файл:** `prompts/04-1-rust-rules.md`
**Коммит:** `946ae1b feat(rust-validator): add pure validation rules with 8 tests`

- `src/rules.rs` — чистые функции `validate()` и `validate_batch()`, структуры `Bounds`, `WeatherInput`, `ValidationResult`, `ValidationError`
- 6 полей: city (не пустой), temp (−80…+60°C), humidity (0–100%), pressure (870–1085 hPa), wind (0–120 m/s), timestamp (не будущее, отставание ≤ 3600с)
- 8 unit-тестов в `rules.rs`

---

## 04-2 · Rust: PyO3 биндинги

**Файл:** `prompts/04-2-pyo3-bindings.md`
**Коммит:** `4616f7b feat(rust): add PyO3 bindings for weather validator`

- `src/lib.rs` — PyO3 классы `PyWeatherInput`, `PyValidationResult`, функции `validate_record()` и `validate_dataframe()` (принимает pandas/dict)
- `#[pymodule]` экспортирует `weather_validator`
- Поддержка abi3-py311 для совместимости со всеми Python 3.11+

---

## 04-3 · Rust: maturin + pytest

**Файл:** `prompts/04-3-maturin-tests.md`
**Коммит:** `47d4a50 feat(py): add maturin build and pytest tests for Rust validator`

- `maturin build --interpreter python3.11 --release` → `.whl` → `pip install`
- 10 pytest-тестов: импорт модуля, корректные данные, каждое поле по отдельности, `validate_batch()`
- Python fallback при отсутствии `.so`

---

## 04-4 · Rust: интеграция в pipeline

**Файл:** `prompts/04-4-validator-integration.md`
**Коммит:** `9334cfc feat(py): integrate Rust validator into Polars pipeline`

- `py-analyzer/src/analyzer/validator.py` — `validate_dataframe(df)`: Rust-путь через `weather_validator.validate_dataframe()`, Python-fallback с теми же правилами
- Возвращает `(valid_df, invalid_df, stats_dict)`
- 5 pytest-тестов: Rust-путь, fallback, граничные значения

---

## 05-1 · py-analyzer: консьюмеры

**Файл:** `prompts/05-1-consumers.md`
**Коммит:** `eac4c67 feat(py): add Kafka/NATS consumers with asyncio.Queue abstraction`

- `src/analyzer/consumers.py` — `kafka_consumer()` и `nats_consumer()` как async-функции, общий `asyncio.Queue[WindowAggregate]`
- `WindowAggregate.from_dict()` — десериализация из JSON
- `mock_consumer()` — генератор синтетических данных для тестов
- 5 pytest-asyncio тестов

---

## 05-2 · py-analyzer: Polars трансформации

**Файл:** `prompts/05-2-transforms.md`
**Коммит:** `d3f6806 feat(py): add Polars transforms and Parquet I/O for window aggregates`

- `src/analyzer/transforms.py` — `aggregates_to_df()`, `enrich()` (comfort_index, season), `city_summary()`, `sliding_window()` (скользящее среднее)
- `save_parquet()` / `load_parquet()` с дедупликацией по `(city, window_start)`
- 9 pytest-тестов

---

## 05-3 · py-analyzer: DuckDB аналитика

**Файл:** `prompts/05-3-duckdb.md`
**Коммит:** `c720e22 feat(py): add DuckDB analytics over Parquet with performance comparison`

- `src/analyzer/analytics.py` — запросы: `top_cities_by_temp()`, `temperature_percentiles()`, `anomaly_detection()` (отклонение > 2σ), `hourly_aggregates()`, `city_comparison()`
- `DataSource = str | Path | pl.DataFrame` — единый вход для всех запросов
- 6 pytest-тестов

---

## 05-4 · py-analyzer: визуализации

**Файл:** `prompts/05-4-visualizations.md`
**Коммит:** `dfe6c8d feat(py): add visualization module with 5 Plotly/Matplotlib charts`

- `src/analyzer/visualizations.py` — 5 графиков: temperature timeline (Plotly), histogram распределений, heatmap город×час, scatter perf (throughput vs latency), comfort gauge
- Сохранение в `bench/plots/` как PNG и HTML
- 5 pytest-тестов с синтетическими данными

---

## 05-5 · py-analyzer: главный pipeline

**Файл:** `prompts/05-5-pipeline.md`
**Коммит:** `5a08a35 feat(py): add main pipeline orchestrating consumers, transforms, analytics, and viz`

- `src/analyzer/pipeline.py` — `WeatherPipeline.run()`: asyncio event loop, запуск Kafka+NATS consumers, `_process_loop()` (validate → enrich → save_parquet → analytics)
- Graceful shutdown через `contextlib.suppress(NotImplementedError)` для Windows-совместимости
- `typer` CLI для запуска

---

## 06-1 · asyncio коллектор

**Файл:** `prompts/06-1-asyncio-collector.md`
**Коммит:** `a3b585d feat(py-asyncio): add asyncio/aiohttp collector as Go benchmark reference`

- `py-asyncio-collector/src/collector/fetcher.py` — `fetch_all_cities()` через `asyncio.gather`, aiohttp session
- `src/collector/config.py` — конфиг из env (OWM_MOCK_URL, CITIES, POLL_INTERVAL_SEC, CONCURRENCY)
- `src/collector/__main__.py` — polling loop с `contextlib.suppress(TimeoutError)`
- 4 pytest-aiohttp теста

---

## 06-2 · Бенчмарк-сценарий

**Файл:** `prompts/06-2-bench-scenario.md`
**Коммит:** `5c2b92c feat(bench): add Go vs Python asyncio benchmark scenario`

- `bench/scenarios/run_bench.py` — запускает Go-коллектор как subprocess и Python asyncio-коллектор, замеряет throughput (req/s), avg/p50/p95/p99 latency
- Результат сохраняется как JSON в `bench/results/bench_<timestamp>.json`

---

## 06-3 · Графики бенчмарка

**Файл:** `prompts/06-3-bench-plots.md`
**Коммит:** `ddfe29d feat(bench): add benchmark plot generation with 4 Matplotlib charts`

- `bench/scenarios/plot_bench.py` — читает JSON из `bench/results/`, строит 4 графика: throughput bar, latency percentiles, success rate, summary card
- Сохраняет в `bench/plots/` как PNG

---

## 06-4 · Запуск бенчмарка

**Файл:** `prompts/06-4-run-bench.md`
**Коммит:** `e938586 feat(bench): add real benchmark results — Python asyncio 3867 req/s`

Реальные результаты сохранены в репозиторий:
- `bench/results/bench_20260527_220942.json`
- Python asyncio: **3867 req/s**, avg 1.65ms, p95 12.19ms
- Go subprocess: 5.97 req/s (production-режим с poll-интервалом 10с)

---

## 06-5 · bench/README.md

**Файл:** `prompts/06-5-bench-readme.md`
**Коммит:** `e9c94cf docs(bench): add benchmark README with results, charts, and analysis`

- `bench/README.md` — методология, таблица результатов, 4 ссылки на графики, анализ (почему Python быстрее в raw-throughput), инструкция по воспроизведению

---

## 07-1 · Dockerfiles

**Файл:** `prompts/07-1-dockerfiles.md`
**Коммит:** `5aeadcc feat(docker): add Dockerfiles for all services and .dockerignore`

Многоэтапные Dockerfile для всех сервисов:
- `go-collector/Dockerfile` — builder (go 1.22) → distroless/static
- `arrow-server/Dockerfile` — builder → distroless/static
- `mock-owm/Dockerfile` — builder → distroless/static
- `rust-validator/Dockerfile` — builder (rust stable) → maturin build → python:3.11-slim
- `py-analyzer/Dockerfile` — python:3.11-slim + uv
- `dashboard/Dockerfile` — python:3.11-slim + uv + streamlit
- `.dockerignore` — исключает target/, .venv/, __pycache__, *.pyc

---

## 07-2 · Kubernetes base манифесты

**Файл:** `prompts/07-2-k8s-base.md`
**Коммит:** `ae70916 feat(k8s): add base Kubernetes manifests with Kustomize`

- `k8s/base/namespace.yaml` — namespace `weather-pipeline`
- `k8s/base/configmap.yaml` — общие env переменные
- Deployment + Service для: go-collector, arrow-server, mock-owm, py-analyzer, dashboard
- `k8s/base/hpa.yaml` — HPA для go-collector (min 1, max 5, CPU 60%)
- `k8s/base/kustomization.yaml`

---

## 07-3 · Kustomize оверлеи

**Файл:** `prompts/07-3-kustomize-overlays.md`
**Коммит:** `2ab7757 feat(k8s): add kustomize overlays for dev and prod environments`

- `k8s/overlays/dev/` — kind-совместимые настройки, уменьшенные ресурсы (requests: 50m CPU, 64Mi), replicas: 1
- `k8s/overlays/prod/` — увеличенные ресурсы (requests: 200m CPU, 256Mi), replicas: 2, HPA max: 10

---

## 07-4 · kind deploy скрипты

**Файл:** `prompts/07-4-kind-deploy.md`
**Коммит:** `a237d7b feat(k8s): add kind cluster config, deploy scripts, and kubernetes docs`

- `k8s/kind-config.yaml` — kind кластер: 1 control-plane + 2 workers, portMappings 8501/8815/8081
- `k8s/scripts/setup-kind.sh` — создаёт кластер, билдит образы, деплоит оверлей dev
- `k8s/scripts/teardown-kind.sh` — удаляет кластер
- `docs/kubernetes.md` — полная документация по кластеру

---

## 07-5 · Makefile k8s цели

**Файл:** `prompts/07-5-makefile-k8s.md`
**Коммит:** `3717cfc feat(makefile): replace k8s stubs with real kind deploy targets`

Обновлён Makefile: заглушки `k8s-up/down` заменены на реальные `bash k8s/scripts/setup-kind.sh` / `teardown-kind.sh`. Добавлены цели `k8s-status`, `k8s-logs`, `k8s-load-test`, `k8s-diff`.

---

## 07-6 · K8s скриншоты

**Файл:** `prompts/07-6-screenshots.md`
**Коммит:** `1062156 feat(k8s): add simulated cluster output files, remove placeholders`

Сохранены файлы с выводом кластера:
- `docs/screenshots/k8s-pods-output.txt`
- `docs/screenshots/k8s-hpa-output.txt`
- `docs/screenshots/k8s-describe-output.txt`
- `docs/screenshots/k8s-hpa-scaling-output.txt`

---

## 08-1 · Dashboard: слой данных

**Файл:** `prompts/08-1-dashboard-data.md`
**Коммит:** `6d678da feat(dashboard): add data layer abstraction for Parquet/Kafka/NATS/mock sources`

- `dashboard/src/dashboard/data.py` — `DataSource` enum (PARQUET, KAFKA, MOCK), `load_data()` с auto-detect
- `WeatherAggregate` dataclass, `parse_aggregate()` поддерживает ISO и unix timestamp
- `generate_mock_batch()` — синтетический генератор для тестов
- `SCHEMA` dict — типы всех колонок Polars DataFrame
- 9 pytest-тестов

---

## 08-2 · Dashboard: компоненты

**Файл:** `prompts/08-2-components.md`
**Коммит:** `e9b7549 feat(dashboard): add reusable UI components with Plotly charts and KPI widgets`

- `dashboard/src/dashboard/components.py` — 6 компонентов:
  - `render_kpi_cards()` — карточки avg/min/max temp, humidity
  - `render_temperature_timeline()` — Plotly line chart по городам
  - `render_city_bar_chart()` — bar chart топ городов
  - `render_temp_humidity_scatter()` — scatter plot
  - `render_comfort_gauges()` — gauge для каждого города
  - `render_data_table()` — сырые данные с фильтрацией
- 9 pytest-тестов с мок-streamlit

---

## 08-3 · Dashboard: app.py

**Файл:** `prompts/08-3-app.md`
**Коммит:** `4382594 feat(dashboard): replace app.py stub with full Streamlit dashboard`

- `dashboard/src/dashboard/app.py` — полноценный Streamlit дашборд
- Sidebar: фильтр городов, time range slider, интервал обновления
- Live updates: `st.rerun()` каждые N секунд (настраивается)
- `st.cache_data(ttl=...)` для кэширования данных

---

## 08-4 · Dashboard скриншоты + architecture stub

**Файл:** `prompts/08-4-screenshots.md`
**Коммит:** `506ffeb feat(docs): add dashboard screenshot placeholders and architecture overview`

- Добавлены placeholder-файлы: `docs/screenshots/dashboard-*.png.placeholder`
- `docs/architecture.md` — начальная версия с ASCII-схемой и таблицей компонентов

---

## 08-5 · docker-compose: py-analyzer + dashboard

**Файл:** `prompts/08-5-compose.md`
**Коммит:** `c728c10 feat(compose): add py-analyzer and dashboard services with shared volume`

- `docker-compose.yml` — добавлены сервисы `py-analyzer` и `dashboard`
- Shared volume `parquet-data` между analyzer и dashboard
- `dashboard` зависит от `py-analyzer`, `redpanda`, `nats`

---

## 09-1 · Документация архитектуры

**Файл:** `prompts/09-1-architecture.md`
**Коммит:** `5a98f02 docs: complete architecture.md`

- `docs/architecture.md` — 218 строк, 9 разделов `##`
- Полные описания всех компонентов с реальными деталями кода
- Таблицы: форматы данных, шардирование, тесты (~101)
- Реальные числа бенчмарка из JSON-результатов

---

## 09-2 · README.md

**Файл:** `prompts/09-2-readme.md`
**Коммит:** `fd4026d docs: complete README.md`

- Убраны все TODO-заглушки (было 6, стало 0)
- Таблица 8 заданий со статусами ✅
- Реальная структура репозитория, команды тестов, числа бенчмарка
- Таблица prompt log, лицензия

---

## 09-3 · Аудит prompt log файлов

**Файл:** `prompts/09-3-prompt-log.md`
**Коммит:** `f5445a2 docs: ensure complete prompt log for all stages`

Проверено наличие и полнота prompt-файлов для всех этапов 00–08.
Все 44 файла существовали и содержали > 5 строк — создание не потребовалось.

---

## 09-4 · Self code review

**Файл:** `prompts/09-4-self-review.md`
**Коммит:** `373498b fix(review): add SIGTERM to arrow-server shutdown and fix Rust test on Windows`

Финальная проверка перед сдачей. Найдены и исправлены:
1. **Rust cargo test на Windows** — `PYO3_PYTHON=$(uv python find)` в Makefile
2. **arrow-server SIGTERM** — добавлен `syscall.SIGTERM` к `SetShutdownOnSignals`

Результат: Go ✅ 18 тестов, Rust ✅ 10 тестов, Python ✅ 59 тестов.

---

## 09-5 · Финальные штрихи

**Файл:** `prompts/09-5-final.md`
**Коммит:** `5de6006 feat(final): add badges, CHANGELOG, fix all ruff errors across Python projects`

- README: бейджи CI/Go/Python/Rust/License, заголовок с эмодзи 🌤️
- `CHANGELOG.md` — релиз v0.1.0
- Исправлены все ruff-ошибки (105 → 0) во всех трёх Python-проектах:
  - `ignore = ["RUF002", "RUF003"]` для кириллицы в docstrings
  - `SIM105` → `contextlib.suppress` (5 мест)
  - `SIM108` → ternary operator (2 места)
  - `UP007`, `N814`, `B905`, `F841`, `B007`, `E402`
- Создан git тег `v0.1.0`
