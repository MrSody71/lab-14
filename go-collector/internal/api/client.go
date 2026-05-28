package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
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

// NewClientWithTimeout creates a Client with a custom HTTP timeout.
func NewClientWithTimeout(baseURL string, timeout time.Duration) *Client {
	return &Client{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}
}

// FetchWeather получает погоду для одного города.
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
	defer func() { _ = resp.Body.Close() }()

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
	defer func() { _ = resp.Body.Close() }()

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
