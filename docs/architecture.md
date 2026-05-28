# Weather Pipeline — Architecture

## Overview

```
OpenWeatherMap (mock)
        │
        ▼
  Go Collector (go-collector/)
  ├── HTTP client → mock-owm (:8081)
  ├── etcd shard coordination (:2379)
  ├── 60-second tumbling windows
  └── Kafka + NATS dual-sink fanout
        │
        ├──────────────────────┐
        ▼                      ▼
  Redpanda (:9092)        NATS JetStream (:4222)
  topic: weather.raw      subject: weather.raw
        │                      │
        └──────────┬────────────┘
                   ▼
         py-analyzer (pipeline/)
         ├── Kafka + NATS asyncio consumers
         ├── Rust validator (PyO3 .so)
         ├── Polars transforms → Parquet
         └── DuckDB analytics
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
  Arrow Flight Server   Streamlit Dashboard
  (arrow-server/ :8815)  (dashboard/ :8501)
        │
        ▼
  Python Flight Client
  (→ Polars DataFrame)
```

## Components

### mock-owm (Go)

Генерирует реалистичные погодные данные для 10 городов.

**Эндпоинты:**
- `GET /health` — статус сервиса
- `GET /data/2.5/weather?q=<city>&units=metric` — данные одного города
- `GET /batch?cities=Moscow,London&units=metric` — пакетный запрос (параллельные горутины)
- Параметр `delay=<ms>` (макс. 2000 ms) — искусственная задержка для тестов

**Генерация данных:** каждый город имеет `BaseTemp` (Kelvin). `Generate()` добавляет случайный шум ±3 K, давление 1000–1030 hPa, влажность 40–95 %, скорость ветра 0–15 m/s.

### go-collector (Go)

Опрашивает mock-owm, накапливает данные в tumbling-окнах, публикует агрегаты.

- **Параллельный опрос:** каждый город опрашивается в отдельной горутине каждые 10 с (`POLL_INTERVAL_SEC`)
- **Tumbling window:** размер 60 с (`WINDOW_SIZE_SEC`), агрегирует avg/min/max temp, avg humidity, pressure, wind
- **Sink fanout:** `Fanout.Run()` читает из одного канала и параллельно публикует в Kafka (`weather.raw`) и NATS (`weather.raw`); ошибка одного sink не останавливает другой
- **Graceful shutdown:** SIGTERM → context cancel → `tw.flush()` → close sinks → exit (timeout 15 с)

### rust-validator (Rust + PyO3)

Валидирует 6 полей по диапазонам `Bounds`:

| Поле | Диапазон |
|------|----------|
| `city` | не пустой |
| `temperature` | −80 … +60 °C |
| `humidity` | 0 … 100 % |
| `pressure` | 870 … 1085 hPa |
| `wind_speed` | 0 … 120 m/s |
| `timestamp` | не из будущего, отставание ≤ 3600 с |

Собирается через `maturin build --interpreter python3.11 --release` в `.so` (abi3-py311). Импортируется в Python как `import weather_validator`. При отсутствии `.so` — Python fallback с теми же правилами.

### py-analyzer (Python)

- **Consumers:** `KafkaConsumer` + NATS `subscribe` → общий `asyncio.Queue`
- **validate_dataframe:** вызывает Rust `.so`; при ImportError — Python fallback
- **Polars transforms:** `enrich` (добавляет comfort_index, season), `city_summary` (агрегация по городам), `sliding_window` (скользящее среднее)
- **DuckDB queries:** топ городов по температуре, перцентили, аномалии (отклонение > 2σ)
- **Parquet sink:** `data/weather_*.parquet` — колоночное хранение для быстрого сканирования
- **Визуализации (5):** timeline, histogram, heatmap, perf-scatter, comfort-gauge

### arrow-server (Go)

Arrow Flight RPC сервер (`arrowsrv/`):

- **Store:** кольцевой буфер `[]AggregateRecord` (потокобезопасный, `sync.RWMutex`), хранит последние N агрегатов
- **DoGet:** тикет `"all"` — все записи; тикет `"<city_name>"` — только этот город
- Читает агрегаты из Kafka, сохраняет в Store; отдаёт клиентам как `arrow.RecordBatch`

### dashboard (Python + Streamlit)

- **DataSource:** auto-detect — parquet → kafka → mock-генератор
- **Компоненты (6):** KPI-карточки, temperature timeline, bar chart городов, scatter (temp vs humidity), comfort gauges, raw data table
- **Live updates:** `st.rerun()` каждые N секунд (настраивается в sidebar)
- **Sidebar:** фильтр городов, диапазон времени, интервал обновления

## Поток данных

1. **mock-owm** генерирует данные при HTTP-запросе — псевдослучайные значения с базовой температурой города
2. **go-collector** каждые 10 с опрашивает свои города (распределённые через etcd-шардирование)
3. **Tumbling window** накапливает показания 60 с, вычисляет avg/min/max по каждому городу
4. **flush** → `WindowAggregate` → Kafka топик `weather.raw`
5. **flush** → `WindowAggregate` → NATS subject `weather.raw` (одновременно через `Fanout`)
6. **py-analyzer** читает из Kafka → валидирует через Rust `.so` → отбрасывает невалидные записи
7. Обогащает DataFrame (comfort_index, season) → сохраняет в Parquet
8. **DuckDB** читает Parquet → SQL-аналитика (топ городов, перцентили, аномалии)
9. **Streamlit dashboard** читает Parquet → обновляет визуализации каждые N с
10. **arrow-server** читает из Kafka → хранит агрегаты в кольцевом буфере памяти
11. **Python Flight client** вызывает `DoGet("all")` → получает `Arrow RecordBatch` → конвертирует в Polars DataFrame

## Форматы данных

| Этап | Формат | Обоснование |
|------|--------|-------------|
| collector → broker | JSON (Kafka / NATS) | простота, совместимость, human-readable |
| analyzer storage | Parquet | колоночный, сжатие Snappy, быстрый scan |
| analyzer → dashboard | Polars DataFrame (in-memory) | zero-copy, lazy evaluation |
| arrow-server → client | Arrow RecordBatch (Flight RPC) | zero-copy, типизированная схема |

## Шардирование (etcd)

Алгоритм `assignCities`:

```
город i → шард: i % len(sorted_shard_ids)
```

- Все shard-id сортируются лексикографически → детерминированный порядок
- Каждый инстанс коллектора регистрируется в etcd с lease TTL = 15 с, keep-alive каждые 5 с
- При падении шарда lease истекает → ключ удаляется → оставшиеся инстансы пересчитывают `MyCities()` и подхватывают города

**Пример (10 городов, 2 шарда):**

| Шард | Индексы | Города |
|------|---------|--------|
| shard-0 | 0, 2, 4, 6, 8 | Moscow, Novosibirsk, Kazan, Stockholm, London |
| shard-1 | 1, 3, 5, 7, 9 | Saint-Petersburg, Yekaterinburg, Berlin, New-York, Tokyo |

## Производительность

Результаты из `bench/results/bench_20260527_220942.json`:

| Метрика | Go collector | Python asyncio |
|---------|-------------|----------------|
| Throughput (req/s) | 5.97 | 3 867 |
| Avg latency (ms) | N/A* | 1.65 |
| P95 latency (ms) | N/A* | 12.19 |
| P99 latency (ms) | N/A* | 12.85 |

\* Go коллектор работает в production-режиме с интервалом опроса 10 с (rate-limited), поэтому latency не измеряется отдельно — throughput отражает реальный темп сбора.

**Вывод:** Python asyncio показывает ~650× более высокий raw HTTP-throughput за счёт event loop без sleep-интервалов. Go коллектор намеренно ограничен production-темпом (10 с/город) и оптимизирован для надёжности (graceful shutdown, etcd sharding), а не для максимального throughput.

## Тестирование

| Компонент | Тестов | Фреймворк | Примечание |
|-----------|--------|-----------|------------|
| mock-owm | 3 | go test + httptest | /weather, /batch, /health |
| go-collector/config | 2 | go test | env var parsing |
| go-collector/api | 5 | go test + httptest | client + types |
| go-collector/shard | 3 | go test (no etcd) | assignCities logic |
| go-collector/window | 3 | go test | tumbling window flush |
| go-collector/sink | 2 | go test | fanout mock |
| rust-validator | 8 | cargo test | rules unit tests |
| rust-validator (PyO3) | 10 | pytest | Python binding tests |
| py-analyzer/consumers | 5 | pytest-asyncio | Kafka + NATS consumers |
| py-analyzer/transforms | 9 | pytest | Polars transforms |
| py-analyzer/analytics | 6 | pytest | DuckDB queries |
| py-analyzer/visualizations | 5 | pytest | Plotly chart generation |
| py-analyzer/validator | 5 | pytest | Rust path + fallback |
| arrow-server | 4 | go test | Store + Flight handlers |
| arrow-client (py) | 4 | pytest + mock server | Flight client |
| py-asyncio-collector | 4 | pytest-aiohttp | async collector |
| bench plots | 5 | pytest | synthetic benchmark data |
| dashboard/data | 9 | pytest | DataSource auto-detect |
| dashboard/components | 9 | pytest (mocked st) | KPI, timeline, gauges |
| **Итого** | **~101** | | |

## Зависимости между сервисами

Порядок запуска:

1. **etcd** — координация шардов (go-collector зависит от него)
2. **redpanda** — Kafka broker (go-collector, arrow-server, py-analyzer)
3. **nats** — JetStream (go-collector, py-analyzer)
4. **mock-owm** — источник данных (go-collector)
5. **go-collector** — зависит от 1–4
6. **arrow-server** — зависит от 2 (Kafka)
7. **py-analyzer** — зависит от 2 (Kafka) и 3 (NATS)
8. **dashboard** — зависит от 7 (Parquet / Kafka / mock fallback)

## Dashboard Screenshots

### Полный вид

> Screenshots will be added after running the dashboard locally.
> Run: `cd dashboard && uv run streamlit run src/dashboard/app.py`

![Dashboard Full View](screenshots/dashboard-full.png)

### KPI Cards

![KPI Cards](screenshots/dashboard-kpi.png)

### Temperature Timeline

![Temperature Timeline](screenshots/dashboard-timeline.png)

### Comfort Gauges

![Comfort Gauges](screenshots/dashboard-gauges.png)

---

See [kubernetes.md](kubernetes.md) for cluster setup and HPA configuration.
