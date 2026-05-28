# Weather Pipeline

## Цель работы

TODO: заполним на этапе X

## Архитектура

TODO: заполним на этапе X

## Технологический стек

| Компонент | Технология |
| --- | --- |
| Сборщик | Go 1.22, net/http, etcd client |
| Валидация | Rust + PyO3 (abi3-py311) |
| Анализ | Python 3.11, Polars, DuckDB, pyarrow |
| Дашборд | Streamlit + Plotly |
| Брокеры | Redpanda (Kafka API) + NATS JetStream |
| Координация | etcd v3.5 |
| Оркестрация | Kubernetes (kind), HPA |

## Структура репозитория

TODO: заполним на этапе X

## Быстрый старт

```bash
# 1. Скопировать конфиг
cp .env.example .env

# 2. Поднять всю инфраструктуру
make docker-up

# 3. Открыть дашборд
open http://localhost:8501

# 4. Проверить Kafka
open http://localhost:8080   # Redpanda Console

# 5. Посмотреть логи
make docker-logs
```

Компоненты:
| Сервис | URL |
|---|---|
| Dashboard | http://localhost:8501 |
| Redpanda Console | http://localhost:8080 |
| Mock OWM API | http://localhost:8081 |
| NATS Monitor | http://localhost:8222 |

## Запуск тестов

TODO: заполним на этапе X

## Развёртывание в Kubernetes

```bash
# Создать кластер и задеплоить
make k8s-up

# Посмотреть состояние
make k8s-status

# Наблюдать за HPA
kubectl get hpa -n weather-pipeline -w

# Нагрузочный тест
make k8s-load-test

# Удалить кластер
make k8s-down
```

Подробнее: [docs/kubernetes.md](docs/kubernetes.md)

## Бенчмарки

См. [bench/README.md](bench/README.md) — Go vs Python asyncio, throughput и latency.

Последний результат: **Python asyncio 3867 req/s** на локальном мок-сервере OWM (15 раундов × 10 городов).

## Prompt log

TODO: заполним на этапе X

## Лицензия

TODO: заполним на этапе X
