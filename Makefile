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
