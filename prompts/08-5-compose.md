Добавь дашборд в docker-compose.yml чтобы
весь стек поднимался одной командой.

В docker-compose.yml добавь сервис после mock-owm:

  py-analyzer:
    build:
      context: ./py-analyzer
    container_name: weather-analyzer
    environment:
      OWM_MOCK_URL: "http://mock-owm:8081"
      KAFKA_BROKERS: "redpanda:9093"
      NATS_URL: "nats://nats:4222"
      PARQUET_PATH: "/data/weather.parquet"
      FLUSH_EVERY: "5"
    volumes:
      - weather-data:/data
    depends_on:
      redpanda:
        condition: service_healthy
      nats:
        condition: service_healthy
      mock-owm:
        condition: service_healthy
    networks: [weather-net]
    restart: unless-stopped
    command: ["uv", "run", "python", "-m",
              "analyzer.pipeline", "--mock"]

  dashboard:
    build:
      context: ./dashboard
    container_name: weather-dashboard
    ports:
      - "8501:8501"
    environment:
      PARQUET_PATH: "/data/weather.parquet"
      KAFKA_BROKERS: "redpanda:9093"
      NATS_URL: "nats://nats:4222"
    volumes:
      - weather-data:/data
    depends_on:
      - py-analyzer
    networks: [weather-net]
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL",
             "wget -q -O- http://localhost:8501/_stcore/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 5

Добавь в конце docker-compose.yml (после networks:) секцию volumes:
  volumes:
    weather-data:
      driver: local

Обнови раздел ## Быстрый старт в корневом README.md:

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

ПРОВЕРКА:
  docker compose config 2>&1 | grep -E "service|container_name" | head -20

  # Проверить что YAML валиден
  python3 -c "
  import yaml
  d = yaml.safe_load(open('docker-compose.yml'))
  services = list(d['services'].keys())
  print('Services:', services)
  assert 'dashboard' in services
  assert 'py-analyzer' in services
  print('OK')
  "

prompts/08-5-compose.md — этот промт целиком.
