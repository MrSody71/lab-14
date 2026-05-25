# Промт 0.1 — Корневые файлы

Прочитай CLAUDE.md, чтобы понять контекст.

Создай только корневые файлы репозитория. Никаких подкаталогов с кодом
на этом шаге — только то, что лежит в корне.

ФАЙЛЫ:

1. README.md — скелет со следующими разделами (используй именно эти
   заголовки уровня ##, под каждым поставь "TODO: заполним на этапе X"):
   # Weather Pipeline
   ## Цель работы
   ## Архитектура
   ## Технологический стек
   ## Структура репозитория
   ## Быстрый старт
   ## Запуск тестов
   ## Развёртывание в Kubernetes
   ## Бенчмарки
   ## Prompt log
   ## Лицензия

   В разделе "Технологический стек" уже впиши таблицу:
   | Компонент | Технология |
   | --- | --- |
   | Сборщик | Go 1.22, net/http, etcd client |
   | Валидация | Rust + PyO3 (abi3-py311) |
   | Анализ | Python 3.11, Polars, DuckDB, pyarrow |
   | Дашборд | Streamlit + Plotly |
   | Брокеры | Redpanda (Kafka API) + NATS JetStream |
   | Координация | etcd v3.5 |
   | Оркестрация | Kubernetes (kind), HPA |

2. .gitignore — объедини шаблоны GitHub для Go, Python, Rust,
   VisualStudioCode, JetBrains, macOS, Linux, Windows. В конце дополни:
   /data/
   /bench/results/
   *.parquet
   *.arrow
   .env
   prompts/.local/
   .claude/

3. .editorconfig:
   root = true
   [*] charset = utf-8, end_of_line = lf, insert_final_newline = true,
       trim_trailing_whitespace = true
   [*.py] indent_style = space, indent_size = 4
   [*.go] indent_style = tab, indent_size = 4
   [*.rs] indent_style = space, indent_size = 4
   [*.{yml,yaml,json,toml}] indent_style = space, indent_size = 2
   [Makefile] indent_style = tab

4. LICENSE — MIT, год 2025, держатель — "Weather Pipeline Authors".

5. .env.example:
   OWM_MOCK_URL=http://localhost:8081
   KAFKA_BROKERS=localhost:9092
   NATS_URL=nats://localhost:4222
   ETCD_ENDPOINTS=localhost:2379
   ARROW_FLIGHT_ADDR=localhost:8815
   CITIES=Moscow,Saint-Petersburg,Novosibirsk,Yekaterinburg,Kazan,Stockholm,Berlin,London,New-York,Tokyo
   POLL_INTERVAL_SEC=10
   WINDOW_SIZE_SEC=60

6. CONTRIBUTING.md — одно правило: "Каждый PR должен добавлять
   prompts/NN-<topic>.md с использованными промтами. Без prompts/ изменения
   не принимаются."

7. prompts/00-1-root-files.md — положи туда этот промт ЦЕЛИКОМ
   (от слова "Прочитай CLAUDE.md" и до конца). Сверху заголовок:
   "# Промт 0.1 — Корневые файлы"

ПРОВЕРКА:
ls -la покажи мне. Убедись, что нет лишних файлов и нет пустых.
В конце: git status.
