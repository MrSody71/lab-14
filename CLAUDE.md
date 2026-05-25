# Контекст проекта для Claude Code

Лабораторная работа №14, вариант 2 — конвейер обработки погодных данных.
Источник данных: мок-сервер OpenWeatherMap (реального API-ключа нет).

## Стек
- Go 1.22 (сборщик, мок OWM, Arrow Flight сервер)
- Rust stable (валидатор через PyO3, abi3-py311)
- Python 3.11+ (Polars, DuckDB, Streamlit, pyarrow, kafka-python, nats-py)
- Брокеры: Redpanda (Kafka API) + NATS JetStream — оба, для сравнения
- Координация шардов: etcd
- Оркестрация: Kubernetes (kind) + HPA

## Правила работы
- Не пиши бизнес-логику без явной просьбы — только то, что требует текущий промт.
- Каждый промт = один атомарный коммит. Не делай ничего сверх задания.
- Все генерируемые промты складывай в prompts/NN-<topic>.md.
- Module path: github.com/USERNAME/weather-pipeline/<subdir> (замени USERNAME ниже).
- Перед завершением задачи запускай проверку из промта и показывай вывод.
- Если проверка падает — чини и повторяй, не спрашивай меня.

## GitHub username
USERNAME = MrSody71