Прочитай CLAUDE.md.

Создай конфигурацию и общие структуры данных для go-collector.
Никакой логики сбора пока — только типы и config.

=== go-collector/internal/config/config.go ===

package config

import (
    "os"
    "strconv"
    "strings"
    "time"
)

type Config struct {
    MockOWMURL      string
    Cities          []string
    PollInterval    time.Duration
    WindowSize      time.Duration
    KafkaBrokers    []string
    KafkaTopic      string
    NATSUrl         string
    NATSSubject     string
    EtcdEndpoints   []string
    ShardID         string
    TotalShards     int
    ArrowFlightAddr string
    BatchSize       int
    ShutdownTimeout time.Duration
}

func Load() *Config {
    return &Config{
        MockOWMURL:      getEnv("OWM_MOCK_URL", "http://localhost:8081"),
        Cities:          strings.Split(getEnv("CITIES",
            "Moscow,Saint-Petersburg,Novosibirsk,Yekaterinburg,Kazan,Stockholm,Berlin,London,New-York,Tokyo"), ","),
        PollInterval:    getDuration("POLL_INTERVAL_SEC", 10) * time.Second,
        WindowSize:      getDuration("WINDOW_SIZE_SEC", 60) * time.Second,
        KafkaBrokers:    strings.Split(getEnv("KAFKA_BROKERS", "localhost:9092"), ","),
        KafkaTopic:      getEnv("KAFKA_TOPIC", "weather.raw"),
        NATSUrl:         getEnv("NATS_URL", "nats://localhost:4222"),
        NATSSubject:     getEnv("NATS_SUBJECT", "weather.raw"),
        EtcdEndpoints:   strings.Split(getEnv("ETCD_ENDPOINTS", "localhost:2379"), ","),
        ShardID:         getEnv("SHARD_ID", "shard-0"),
        TotalShards:     getInt("TOTAL_SHARDS", 1),
        ArrowFlightAddr: getEnv("ARROW_FLIGHT_ADDR", "localhost:8815"),
        BatchSize:       getInt("BATCH_SIZE", 50),
        ShutdownTimeout: getDuration("SHUTDOWN_TIMEOUT_SEC", 15) * time.Second,
    }
}

func getEnv(key, def string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return def
}

func getInt(key string, def int) int {
    if v := os.Getenv(key); v != "" {
        if i, err := strconv.Atoi(v); err == nil {
            return i
        }
    }
    return def
}

func getDuration(key string, defSec int64) time.Duration {
    if v := os.Getenv(key); v != "" {
        if i, err := strconv.ParseInt(v, 10, 64); err == nil {
            return time.Duration(i)
        }
    }
    return time.Duration(defSec)
}

=== go-collector/internal/config/config_test.go ===

Тесты:
- TestLoadDefaults: Load() без env-переменных возвращает MockOWMURL
  содержащий "localhost:8081", len(Cities)==10, PollInterval==10s
- TestLoadFromEnv: задать t.Setenv("TOTAL_SHARDS","3") и проверить
  что TotalShards==3

=== go-collector/internal/api/types.go ===

package api

import "time"

// WeatherReading — одна запись о погоде, полученная от мок-сервера.
type WeatherReading struct {
    CityName    string    `json:"city"`
    Country     string    `json:"country"`
    Lat         float64   `json:"lat"`
    Lon         float64   `json:"lon"`
    Temperature float64   `json:"temperature"`  // °C
    FeelsLike   float64   `json:"feels_like"`
    TempMin     float64   `json:"temp_min"`
    TempMax     float64   `json:"temp_max"`
    Pressure    int       `json:"pressure"`
    Humidity    int       `json:"humidity"`
    WindSpeed   float64   `json:"wind_speed"`
    WindDeg     int       `json:"wind_deg"`
    CloudsAll   int       `json:"clouds_all"`
    Description string    `json:"description"`
    CollectedAt time.Time `json:"collected_at"`
    ShardID     string    `json:"shard_id"`
}

// WindowAggregate — результат tumbling-window агрегации по одному городу.
type WindowAggregate struct {
    CityName    string    `json:"city"`
    WindowStart time.Time `json:"window_start"`
    WindowEnd   time.Time `json:"window_end"`
    Count       int       `json:"count"`
    AvgTemp     float64   `json:"avg_temp"`
    MinTemp     float64   `json:"min_temp"`
    MaxTemp     float64   `json:"max_temp"`
    AvgHumidity float64   `json:"avg_humidity"`
    AvgPressure float64   `json:"avg_pressure"`
    AvgWindSpeed float64  `json:"avg_wind_speed"`
    ShardID     string    `json:"shard_id"`
}

// OWMResponse — структура ответа мок-сервера (units=metric).
type OWMResponse struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
    Dt   int64  `json:"dt"`
    Main struct {
        Temp      float64 `json:"temp"`
        FeelsLike float64 `json:"feels_like"`
        TempMin   float64 `json:"temp_min"`
        TempMax   float64 `json:"temp_max"`
        Pressure  int     `json:"pressure"`
        Humidity  int     `json:"humidity"`
    } `json:"main"`
    Wind struct {
        Speed float64 `json:"speed"`
        Deg   int     `json:"deg"`
    } `json:"wind"`
    Clouds struct {
        All int `json:"all"`
    } `json:"clouds"`
    Weather []struct {
        Description string `json:"description"`
        Icon        string `json:"icon"`
    } `json:"weather"`
    Coord struct {
        Lat float64 `json:"lat"`
        Lon float64 `json:"lon"`
    } `json:"coord"`
    Sys struct {
        Country string `json:"country"`
    } `json:"sys"`
}

// ToReading конвертирует OWMResponse в WeatherReading.
func (r OWMResponse) ToReading(shardID string) WeatherReading {
    desc := ""
    if len(r.Weather) > 0 {
        desc = r.Weather[0].Description
    }
    return WeatherReading{
        CityName:    r.Name,
        Country:     r.Sys.Country,
        Lat:         r.Coord.Lat,
        Lon:         r.Coord.Lon,
        Temperature: r.Main.Temp,
        FeelsLike:   r.Main.FeelsLike,
        TempMin:     r.Main.TempMin,
        TempMax:     r.Main.TempMax,
        Pressure:    r.Main.Pressure,
        Humidity:    r.Main.Humidity,
        WindSpeed:   r.Wind.Speed,
        WindDeg:     r.Wind.Deg,
        CloudsAll:   r.Clouds.All,
        Description: desc,
        CollectedAt: time.Now().UTC(),
        ShardID:     shardID,
    }
}

=== go-collector/internal/api/types_test.go ===

Тест TestToReading: создать OWMResponse с заполненными полями,
вызвать ToReading("shard-0"), проверить что Temperature совпадает,
ShardID == "shard-0", CollectedAt не IsZero.

ПРОВЕРКА:
  go build ./go-collector/... 2>&1 && echo "BUILD OK"
  go test ./go-collector/internal/config/... -v 2>&1
  go test ./go-collector/internal/api/... -v 2>&1

Все тесты зелёные. Если нет — чини.

prompts/02-1-config-types.md — этот промт целиком.
