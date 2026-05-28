# Промт 09-1: Документация архитектуры

## Задача

Заполнить `docs/architecture.md` по шаблону из CLAUDE.md (раздел «Документация»).

## Содержание

Файл должен включать следующие разделы (>120 строк, ≥8 разделов `##`):

### Компоненты
- **mock-owm (Go):** назначение, эндпоинты (/weather, /batch, /health, delay param), генерация данных (10 городов, реалистичные диапазоны)
- **go-collector (Go):** параллельный опрос городов, etcd-шардирование (assignCities), tumbling window (формула агрегации, 60 с), sink fanout (Kafka + NATS), graceful shutdown
- **rust-validator (Rust + PyO3):** 6 полей, диапазоны из Bounds, maturin → .so → import, Python fallback
- **py-analyzer (Python):** Kafka+NATS asyncio consumers, validate_dataframe (Rust + fallback), Polars transforms, DuckDB queries, 5 визуализаций
- **arrow-server (Go):** Arrow Flight RPC, кольцевой буфер Store, DoGet (all / city_name), Python клиент
- **dashboard (Python + Streamlit):** DataSource auto-detect, 6 компонентов, live updates, sidebar

### Поток данных (10 шагов)
1. mock-owm генерирует погоду при HTTP-запросе
2. go-collector каждые 10 с опрашивает свои города (шард)
3. tumbling window накапливает данные 60 с
4. flush → WindowAggregate → Kafka топик weather.raw
5. flush → WindowAggregate → NATS subject weather.raw
6. py-analyzer читает из Kafka → валидирует через Rust
7. enriches DataFrame → сохраняет в Parquet
8. DuckDB читает Parquet → SQL аналитика
9. Streamlit читает Parquet → обновляет дашборд
10. arrow-server читает из Kafka → хранит в памяти → Python Flight клиент

### Форматы данных (таблица)
| Этап | Формат | Обоснование |
|------|--------|-------------|
| collector → broker | JSON (NATS/Kafka) | простота, совместимость |
| analyzer storage | Parquet | колоночный, сжатие, fast scan |
| analyzer → dashboard | Polars DataFrame (in-memory) | zero-copy |
| arrow-server → client | Arrow RecordBatch (Flight RPC) | zero-copy, типизация |

### Шардирование (etcd)
- Алгоритм assignCities: город i → шард i % M
- Lease TTL: 15 с, keep-alive: 5 с
- Пример: 10 городов, 2 шарда

### Производительность (из bench/results/)
| Метрика | Go collector | Python asyncio |
|---------|-------------|----------------|
| Throughput (req/s) | 5.97 | 3867 |
| Avg latency (ms) | N/A | 1.65 |
| P95 latency (ms) | N/A | 12.19 |

### Тестирование (таблица ~101 теста)

### Зависимости между сервисами (startup order: etcd → redpanda → nats → mock-owm → go-collector → arrow-server → py-analyzer → dashboard)

### Dashboard Screenshots (placeholders)

## Проверка

```bash
wc -l docs/architecture.md
# Должно быть > 120 строк

grep -c "^## " docs/architecture.md
# Должно быть >= 8 разделов
```
