Нужно запустить бенчмарк, получить реальные результаты
и сохранить их в репозиторий.

ШАГ 1 — Поднять мок-сервер:
  go run ./mock-owm/cmd/mockowm &
  # подождать 2 секунды
  На Windows: запусти в отдельном терминале

ШАГ 2 — Проверить что мок отвечает:
  curl -s http://localhost:8081/health
  # должно быть {"status":"ok","cities":10}

ШАГ 3 — Собрать Go-коллектор для бенча:
  go build -o bench/go_collector ./go-collector/cmd/collector
  # Windows:
  # go build -o bench/go_collector.exe ./go-collector/cmd/collector

ШАГ 4 — Запустить бенчмарк:
  cd py-asyncio-collector
  BENCH_ROUNDS=15 OWM_MOCK_URL=http://localhost:8081 \
    uv run python ../bench/scenarios/run_bench.py
  cd ..

  На Windows PowerShell:
  cd py-asyncio-collector
  $env:BENCH_ROUNDS="15"
  $env:OWM_MOCK_URL="http://localhost:8081"
  uv run python ../bench/scenarios/run_bench.py
  cd ..

ШАГ 5 — Проверить результаты:
  ls bench/results/           # должен быть bench_TIMESTAMP.json
  ls bench/plots/             # должны быть 4 PNG файла

  Покажи мне содержимое bench/results/*.json (или последнего файла)
  и убедись что throughput_rps > 0 у Python.

ШАГ 6 — Добавить результаты в .gitignore исключение.
  В .gitignore найди строку /bench/results/ и УДАЛИ её —
  нам нужно закоммитить результаты в репозиторий для проверки.
  Строку /bench/plots/ тоже удали.

ШАГ 7 — Остановить мок-сервер:
  kill %1   # Linux/Mac
  # Windows: закрыть терминал

Покажи мне итоговую таблицу из stdout run_bench.py.

prompts/06-4-run-bench.md — этот промт целиком.
