# Промт 09-2: Заполнение корневого README.md

## Задача

Заполнить `README.md` реальным содержимым — убрать все TODO-заглушки.

## Разделы для замены

### ## Цель работы
Лабораторная работа №14, вариант 2, повышенный уровень.
Таблица выполненных заданий (8 пунктов, все ✅).

### ## Архитектура
Краткая ASCII-схема потока данных + ссылка на docs/architecture.md.

### ## Технологический стек
Дополнить таблицу: добавить Arrow Flight и строку сборки (uv / Cargo / Go workspace).

### ## Структура репозитория
Реальный tree с комментариями ко всем директориям.

### ## Запуск тестов
```bash
make test / make test-go / make test-rust / make test-py
cd py-analyzer && uv run pytest tests/ -v
cd py-analyzer && uv run pytest --cov=analyzer tests/
```
Итог: ~101 тест (Go: 18, Rust: 18, Python: 65).

### ## Бенчмарки
Реальные числа из bench/results/bench_20260527_220942.json:
- Python asyncio: 3867 req/s, avg 1.65 ms, p95 12.19 ms
- Go subprocess: 5.97 req/s (production-режим, не raw throughput)
Таблица + ссылка на bench/README.md + ссылка на графики.

### ## Prompt log
Таблица этапов 0–9, всего 44 промта.

### ## Лицензия
MIT © 2026 MrSody71

## Проверка

```bash
grep -c "TODO" README.md
# Должно быть 0

wc -l README.md
# Должно быть > 100 строк

grep "✅" README.md | wc -l
# Должно быть >= 8 (все задания)
```
