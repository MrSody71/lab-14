Прочитай CLAUDE.md.

Реализуй мок-сервер OpenWeatherMap в mock-owm/. Это Go-программа,
которая поднимает HTTP-сервер и отдаёт реалистичные погодные данные.
Никакого реального API — всё генерируем сами.

=== mock-owm/internal/generator.go ===

Пакет generator. Структуры и функция генерации:

type WeatherData struct {
    CityID      int     `json:"id"`
    CityName    string  `json:"name"`
    Timestamp   int64   `json:"dt"`
    Temperature float64 `json:"temp"`      // в Кельвинах, как в OWM
    FeelsLike   float64 `json:"feels_like"`
    TempMin     float64 `json:"temp_min"`
    TempMax     float64 `json:"temp_max"`
    Pressure    int     `json:"pressure"`  // hPa
    Humidity    int     `json:"humidity"`  // %
    WindSpeed   float64 `json:"wind_speed"`// м/с
    WindDeg     int     `json:"wind_deg"`
    CloudsAll   int     `json:"clouds_all"`// %
    Description string  `json:"description"`
    Icon        string  `json:"icon"`
    Country     string  `json:"country"`
    Lat         float64 `json:"lat"`
    Lon         float64 `json:"lon"`
}

Функция Generate(city string, baseTemp float64) WeatherData:
- Timestamp = time.Now().Unix()
- Temperature = baseTemp + случайное смещение [-3, +3] (math/rand)
- FeelsLike = Temperature - 2 + rand[-1,1]
- TempMin = Temperature - rand[0,2]
- TempMax = Temperature + rand[0,2]
- Pressure = 1000 + rand[0,30]
- Humidity = 40 + rand[0,55]
- WindSpeed = rand[0,15] с точностью 0.1
- WindDeg = rand[0,360]
- CloudsAll = rand[0,100]
- Description — выбрать случайно из: "clear sky","few clouds",
  "scattered clouds","broken clouds","shower rain","rain",
  "thunderstorm","snow","mist"
- Icon — по описанию: "clear sky"→"01d", "few clouds"→"02d",
  "scattered clouds"→"03d", остальные → "04d"
- Country, Lat, Lon — передаются снаружи

Добавь карту cities map[string]CityMeta с 10 городами:
    Moscow:             {ID:524901, Country:"RU", Lat:55.75, Lon:37.62, BaseTemp:278}
    Saint-Petersburg:   {ID:498817, Country:"RU", Lat:59.95, Lon:30.32, BaseTemp:275}
    Novosibirsk:        {ID:1496747,Country:"RU", Lat:54.99, Lon:82.90, BaseTemp:273}
    Yekaterinburg:      {ID:1486209,Country:"RU", Lat:56.85, Lon:60.61, BaseTemp:274}
    Kazan:              {ID:551487, Country:"RU", Lat:55.79, Lon:49.12, BaseTemp:276}
    Stockholm:          {ID:2673730,Country:"SE", Lat:59.33, Lon:18.07, BaseTemp:280}
    Berlin:             {ID:2950159,Country:"DE", Lat:52.52, Lon:13.40, BaseTemp:282}
    London:             {ID:2643743,Country:"GB", Lat:51.51, Lon:-0.13, BaseTemp:284}
    New-York:           {ID:5128581,Country:"US", Lat:40.71, Lon:-74.01,BaseTemp:288}
    Tokyo:              {ID:1850147,Country:"JP", Lat:35.69, Lon:139.69,BaseTemp:290}

Функция GenerateForCity(cityName string) (WeatherData, error):
  ищет cityName в карте (case-insensitive), если не найден — error.

=== mock-owm/internal/handler.go ===

Пакет: тот же (internal назови owmgen или просто internal — на твоё усмотрение,
главное единообразие).

HTTP-хендлеры:

GET /health
  → 200 JSON {"status":"ok","cities":10}

GET /data/2.5/weather?q=<city>&units=metric
  → генерирует WeatherData, возвращает JSON в формате OWM:
  {
    "id": <CityID>,
    "name": <CityName>,
    "dt": <Timestamp>,
    "main": {
      "temp": <Temperature - 273.15 если units=metric>,
      "feels_like": <...>,
      "temp_min": <...>,
      "temp_max": <...>,
      "pressure": <Pressure>,
      "humidity": <Humidity>
    },
    "wind": {"speed": <WindSpeed>, "deg": <WindDeg>},
    "clouds": {"all": <CloudsAll>},
    "weather": [{"description": <Description>, "icon": <Icon>}],
    "coord": {"lat": <Lat>, "lon": <Lon>},
    "sys": {"country": <Country>}
  }
  Если город не найден → 404 JSON {"cod":"404","message":"city not found"}
  Если units=metric — конвертируй Кельвины в Цельсии для полей temp, 
  feels_like, temp_min, temp_max. По умолчанию (без units) — Кельвины.

GET /data/2.5/weather?q=<city>&units=metric&delay=<ms>
  Параметр delay (опциональный, int, ms) — искусственная задержка.
  Нужен для бенчмарков. Max delay = 2000ms, игнорировать если больше.

GET /batch?cities=Moscow,London,Tokyo&units=metric
  Возвращает JSON-массив из WeatherData для всех запрошенных городов.
  Генерировать параллельно через горутины.

=== mock-owm/cmd/mockowm/main.go ===

Заменить заглушку на реальный main:
- Читать адрес из env MOCK_OWM_ADDR (default ":8081")
- Читать seed из env MOCK_OWM_SEED (int64, default = time.Now().UnixNano())
  и инициализировать rand с этим seed (для воспроизводимости в тестах)
- Логировать запросы (метод, путь, статус, latency) через log/slog
- Graceful shutdown: http.Server с таймаутами (Read:5s, Write:10s, Idle:30s)
  + context с cancel по SIGINT/SIGTERM, Shutdown(ctx) с таймаутом 5s

=== mock-owm/internal/generator_test.go ===

Тесты:
- TestGenerateForKnownCity: GenerateForCity("Moscow") не возвращает error,
  Temperature в диапазоне [200, 350] (Кельвин), Humidity в [0,100],
  Pressure > 900
- TestGenerateForUnknownCity: GenerateForCity("Atlantis") возвращает error
- TestBatchEndpoint: запустить тестовый HTTP-сервер через httptest.NewServer,
  GET /batch?cities=Moscow,London, проверить что вернулось 2 объекта

=== mock-owm/Dockerfile ===

FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o mockowm ./cmd/mockowm

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/mockowm .
EXPOSE 8081
ENV MOCK_OWM_ADDR=":8081"
CMD ["./mockowm"]

Обновить docker-compose.yml: добавить сервис mock-owm:
  build:
    context: ./mock-owm
  container_name: weather-mock-owm
  ports: ["8081:8081"]
  environment:
    MOCK_OWM_ADDR: ":8081"
    MOCK_OWM_SEED: "42"
  healthcheck:
    test: ["CMD-SHELL", "wget -q -O- http://localhost:8081/health || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 5
  networks: [weather-net]
  restart: unless-stopped

ОБНОВИТЬ mock-owm/go.mod — добавить require если нужны внешние зависимости.
Если только stdlib — ничего не добавлять.

ПРОВЕРКА (покажи вывод каждой команды):
  cd mock-owm && go build ./... 2>&1 && echo "BUILD OK"
  go test ./... -v -count=1 2>&1
  cd ..
  docker compose config 2>&1 | grep -A5 "mock-owm"

Если тесты падают — чини до зелёного.

prompts/01-1-mock-owm.md — этот промт целиком.
