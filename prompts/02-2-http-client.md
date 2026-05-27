Прочитай CLAUDE.md.

Реализуй HTTP-клиент для опроса мок-сервера OWM.
Конфиг и типы уже есть в internal/config и internal/api.

=== go-collector/internal/api/client.go ===

package api

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type Client struct {
    baseURL    string
    httpClient *http.Client
}

func NewClient(baseURL string) *Client {
    return &Client{
        baseURL: baseURL,
        httpClient: &http.Client{
            Timeout: 10 * time.Second,
        },
    }
}

// FetchWeather получает погоду для одного города.
// Возвращает WeatherReading или ошибку.
func (c *Client) FetchWeather(ctx context.Context, city, shardID string) (WeatherReading, error) {
    url := fmt.Sprintf("%s/data/2.5/weather?q=%s&units=metric", c.baseURL, city)
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return WeatherReading{}, fmt.Errorf("build request: %w", err)
    }
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return WeatherReading{}, fmt.Errorf("fetch %s: %w", city, err)
    }
    defer resp.Body.Close()

    if resp.StatusCode == http.StatusNotFound {
        return WeatherReading{}, fmt.Errorf("city not found: %s", city)
    }
    if resp.StatusCode != http.StatusOK {
        return WeatherReading{}, fmt.Errorf("unexpected status %d for city %s",
            resp.StatusCode, city)
    }

    var owm OWMResponse
    if err := json.NewDecoder(resp.Body).Decode(&owm); err != nil {
        return WeatherReading{}, fmt.Errorf("decode response: %w", err)
    }
    return owm.ToReading(shardID), nil
}

// FetchBatch получает погоду для нескольких городов через /batch.
// Возвращает слайс успешных результатов и слайс ошибок.
func (c *Client) FetchBatch(ctx context.Context, cities []string,
    shardID string) ([]WeatherReading, []error) {
    
    if len(cities) == 0 {
        return nil, nil
    }
    url := fmt.Sprintf("%s/batch?cities=%s&units=metric",
        c.baseURL, strings.Join(cities, ","))
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return nil, []error{fmt.Errorf("build batch request: %w", err)}
    }
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, []error{fmt.Errorf("fetch batch: %w", err)}
    }
    defer resp.Body.Close()

    var owmList []OWMResponse
    if err := json.NewDecoder(resp.Body).Decode(&owmList); err != nil {
        return nil, []error{fmt.Errorf("decode batch: %w", err)}
    }

    readings := make([]WeatherReading, 0, len(owmList))
    for _, o := range owmList {
        readings = append(readings, o.ToReading(shardID))
    }
    return readings, nil
}

Добавь импорт "strings" который потребуется для FetchBatch.

=== go-collector/internal/api/client_test.go ===

Используй httptest.NewServer для создания тестового сервера.

TestFetchWeather_Success:
- поднять httptest.NewServer, который при GET /data/2.5/weather
  возвращает валидный OWMResponse JSON (захардкодить для Moscow)
- NewClient(server.URL).FetchWeather(ctx, "Moscow", "shard-0")
- проверить err==nil, reading.CityName=="Moscow", reading.Temperature!=0

TestFetchWeather_NotFound:
- сервер возвращает 404 {"cod":"404","message":"city not found"}
- FetchWeather должен вернуть ошибку содержащую "city not found"

TestFetchWeather_Timeout:
- сервер делает time.Sleep(2s) перед ответом
- NewClient с Timeout=500ms
- ошибка должна содержать context или timeout

TestFetchBatch_Success:
- сервер возвращает JSON-массив из 2 OWMResponse
- FetchBatch возвращает 2 WeatherReading, ошибок нет

ПРОВЕРКА:
  go build ./go-collector/... 2>&1 && echo "BUILD OK"
  go test ./go-collector/internal/api/... -v -count=1 2>&1

Все 4 теста зелёные.

prompts/02-2-http-client.md — этот промт целиком.
