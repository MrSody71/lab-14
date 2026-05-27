Прочитай CLAUDE.md.

Мок-сервер написан. Нужно запустить его и убедиться что он отвечает.

Выполни последовательно:

1. go run ./mock-owm/cmd/mockowm &
   sleep 2

2. Проверь каждый эндпоинт через curl (или Invoke-WebRequest если curl нет):

   curl -s "http://localhost:8081/health" | python3 -m json.tool
   curl -s "http://localhost:8081/data/2.5/weather?q=Moscow&units=metric" | python3 -m json.tool
   curl -s "http://localhost:8081/data/2.5/weather?q=Tokyo&units=metric" | python3 -m json.tool
   curl -s "http://localhost:8081/data/2.5/weather?q=Atlantis" | python3 -m json.tool
   curl -s "http://localhost:8081/batch?cities=Moscow,London,Stockholm&units=metric" | python3 -m json.tool
   curl -s "http://localhost:8081/data/2.5/weather?q=Berlin&units=metric&delay=500"

3. Для каждого запроса проверь:
   - /health → {"status":"ok","cities":10}
   - /weather Moscow → есть поля main.temp (число), main.humidity (0-100),
     name="Moscow", sys.country="RU"
   - /weather Atlantis → {"cod":"404",...}
   - /batch → JSON-массив из 3 объектов
   - /weather с delay=500 → ответ пришёл через ~500ms (измерь через
     time curl или Measure-Command)

4. Останови сервер: kill %1 (Linux/Mac) или остановить процесс (Windows)

Если что-то не работает — исправь код и повтори.
Покажи мне вывод всех curl-запросов.

prompts/01-2-mock-owm-smoke.md — этот промт целиком.
