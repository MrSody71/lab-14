# Промт 0.6 — docker-compose.yml и Makefile

Прочитай CLAUDE.md.

Создай docker-compose.yml в корне и Makefile. Бизнес-сервисы (collector,
analyzer) сюда НЕ добавляй — они появятся позже. Только инфраструктура.

=== docker-compose.yml ===

services:
  redpanda:
    image: docker.redpanda.com/redpandadata/redpanda:v24.2.7
    container_name: weather-redpanda
    command:
      - redpanda
      - start
      - --kafka-addr internal://0.0.0.0:9093,external://0.0.0.0:9092
      - --advertise-kafka-addr internal://redpanda:9093,external://localhost:9092
      - --pandaproxy-addr internal://0.0.0.0:8083,external://0.0.0.0:18082
      - --advertise-pandaproxy-addr internal://redpanda:8083,external://localhost:18082
      - --schema-registry-addr internal://0.0.0.0:8081,external://0.0.0.0:18081
      - --rpc-addr redpanda:33145
      - --advertise-rpc-addr redpanda:33145
      - --smp 1
      - --memory 1G
      - --mode dev-container
      - --default-log-level=warn
    ports:
      - "9092:9092"
      - "9644:9644"
    healthcheck:
      test: ["CMD-SHELL", "rpk cluster health | grep -E 'Healthy:.+true'"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks: [weather-net]
    restart: unless-stopped

  redpanda-console:
    image: docker.redpanda.com/redpandadata/console:v2.7.2
    container_name: weather-redpanda-console
    entrypoint: /bin/sh
    command: -c 'echo "$$CONSOLE_CONFIG_FILE" > /tmp/config.yml; /app/console'
    environment:
      CONFIG_FILEPATH: /tmp/config.yml
      CONSOLE_CONFIG_FILE: |
        kafka:
          brokers: ["redpanda:9093"]
    ports:
      - "8080:8080"
    depends_on:
      redpanda:
        condition: service_healthy
    networks: [weather-net]
    restart: unless-stopped

  nats:
    image: nats:2.10-alpine
    container_name: weather-nats
    command: ["-js", "-m", "8222"]
    ports:
      - "4222:4222"
      - "8222:8222"
    healthcheck:
      test: ["CMD", "wget", "-q", "-O-", "http://localhost:8222/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [weather-net]
    restart: unless-stopped

  etcd:
    image: quay.io/coreos/etcd:v3.5.15
    container_name: weather-etcd
    environment:
      ETCD_NAME: etcd0
      ETCD_LISTEN_CLIENT_URLS: http://0.0.0.0:2379
      ETCD_ADVERTISE_CLIENT_URLS: http://etcd:2379
      ETCD_LISTEN_PEER_URLS: http://0.0.0.0:2380
      ETCD_INITIAL_CLUSTER: etcd0=http://etcd:2380
      ETCD_INITIAL_CLUSTER_STATE: new
      ETCD_INITIAL_CLUSTER_TOKEN: weather-token
      ETCD_INITIAL_ADVERTISE_PEER_URLS: http://etcd:2380
      ALLOW_NONE_AUTHENTICATION: "yes"
    ports:
      - "2379:2379"
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [weather-net]
    restart: unless-stopped

networks:
  weather-net:
    driver: bridge

ВАЖНО: сервис mock-owm в этот compose НЕ добавляй — он появится в
этапе 1, когда мы его напишем. Сейчас только инфраструктура.

=== Makefile ===

POSIX-совместимый, табы для отступов, цели с комментариями "##" для help.
Целевые команды:

.DEFAULT_GOAL := help

help: ## Показать все цели
    @awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Установить все зависимости
    go work sync
    cd rust-validator && cargo fetch
    cd py-analyzer && uv sync
    cd py-asyncio-collector && uv sync
    cd dashboard && uv sync

build-go: ## Собрать все Go-модули
    go build ./go-collector/...
    go build ./arrow-server/...
    go build ./mock-owm/...

build-rust: ## Собрать Rust-валидатор
    cd rust-validator && cargo build --release

build: build-go build-rust ## Собрать всё

test-go: ## Тесты Go
    go test ./go-collector/... ./arrow-server/... ./mock-owm/... -race -count=1

test-rust: ## Тесты Rust
    cd rust-validator && cargo test

test-py: ## Тесты Python
    cd py-analyzer && uv run pytest
    cd py-asyncio-collector && uv run pytest
    cd dashboard && uv run pytest

test: test-go test-rust test-py ## Все тесты

lint-go: ## Линт Go
    golangci-lint run ./go-collector/... ./arrow-server/... ./mock-owm/...

lint-rust: ## Линт Rust
    cd rust-validator && cargo fmt --check && cargo clippy --all-targets -- -D warnings

lint-py: ## Линт Python
    cd py-analyzer && uv run ruff check
    cd py-asyncio-collector && uv run ruff check
    cd dashboard && uv run ruff check

lint: lint-go lint-rust lint-py ## Все линтеры

fmt: ## Форматирование
    gofmt -s -w go-collector arrow-server mock-owm
    cd rust-validator && cargo fmt
    cd py-analyzer && uv run ruff format
    cd py-asyncio-collector && uv run ruff format
    cd dashboard && uv run ruff format

docker-up: ## Поднять инфраструктуру
    docker compose up -d

docker-down: ## Остановить инфраструктуру
    docker compose down

docker-logs: ## Логи всех сервисов
    docker compose logs -f

k8s-up: ## Развернуть в Kubernetes (заглушка, появится в этапе 7)
    @echo "TODO: implemented in stage 7"

k8s-down: ## Удалить из Kubernetes (заглушка)
    @echo "TODO: implemented in stage 7"

clean: ## Очистить артефакты сборки
    go clean -cache -testcache
    cd rust-validator && cargo clean
    rm -rf bench/results/*.json bench/results/*.csv
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type d -name .pytest_cache -exec rm -rf {} +

.PHONY: help bootstrap build-go build-rust build test-go test-rust test-py test \
        lint-go lint-rust lint-py lint fmt docker-up docker-down docker-logs \
        k8s-up k8s-down clean

ПРОВЕРКА:
  docker compose config              # валидация YAML
  make help                          # должен показать список целей
  make build                         # должен собрать всё
  make test                          # все тесты должны пройти

Если docker compose не установлен — скажи ОДНОЙ строкой
"docker compose not installed", но Makefile всё равно создай и make help
запусти.

prompts/00-6-compose-makefile.md — этот промт целиком.

В конце: git status.
