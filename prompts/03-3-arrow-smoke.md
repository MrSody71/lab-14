Прочитай CLAUDE.md.

Нужно проверить, что Go Arrow Flight сервер и Python клиент
работают вместе. Напиши интеграционный тест и скрипт.

=== py-analyzer/tests/test_arrow_integration.py ===

Интеграционный тест: запускает Go Flight сервер как subprocess,
подключается Python-клиентом, проверяет что данные получены.

Тест пропускается (pytest.mark.skip) если Go бинарник не собран.

Бинарник ищется по пути:
  Path(__file__).parent.parent.parent / "arrow-server" / "arrowsrv"
На Windows: если нет без .exe — добавить .exe суффикс.

Фикстура arrow_server_process (scope=module):
  - env ARROW_FLIGHT_ADDR=":18815", ARROW_MAX_RECORDS="100"
  - subprocess.Popen, sleep(2), yield, terminate

test_fetch_all_empty — df пустой (сервер только запущен)
test_schema_correct — все 11 колонок присутствуют

=== py-analyzer/src/analyzer/demo_arrow.py ===

Демо-скрипт: подключается к Arrow Flight серверу и печатает данные.
Запуск: python -m analyzer.demo_arrow

- Читает ARROW_FLIGHT_HOST / ARROW_FLIGHT_PORT из env
- Подключается, fetch_all(), печатает через rich.Table
- При ошибке или пустых данных — понятное сообщение

Добавить в pyproject.toml:
  [tool.pytest.ini_options]
  markers = ["integration: requires running services"]

ПРОВЕРКА:
  go build -o arrow-server/arrowsrv ./arrow-server/cmd/arrowsrv
  cd py-analyzer
  pytest tests/ -v -m "not integration"         # 5 passed
  pytest tests/test_arrow_integration.py -v -m integration  # 2 passed

prompts/03-3-arrow-smoke.md — этот промт целиком.
