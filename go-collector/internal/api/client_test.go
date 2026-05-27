package api

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func moscowOWM() OWMResponse {
	var o OWMResponse
	o.ID = 524901
	o.Name = "Moscow"
	o.Dt = 1700000000
	o.Main.Temp = 6.5
	o.Main.FeelsLike = 4.0
	o.Main.TempMin = 5.0
	o.Main.TempMax = 8.0
	o.Main.Pressure = 1015
	o.Main.Humidity = 70
	o.Wind.Speed = 3.0
	o.Wind.Deg = 90
	o.Clouds.All = 30
	o.Weather = []struct {
		Description string `json:"description"`
		Icon        string `json:"icon"`
	}{{Description: "few clouds", Icon: "02d"}}
	o.Coord.Lat = 55.75
	o.Coord.Lon = 37.62
	o.Sys.Country = "RU"
	return o
}

func TestFetchWeather_Success(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(moscowOWM())
	}))
	defer srv.Close()

	ctx := context.Background()
	reading, err := NewClient(srv.URL).FetchWeather(ctx, "Moscow", "shard-0")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if reading.CityName != "Moscow" {
		t.Errorf("CityName = %q, want Moscow", reading.CityName)
	}
	if reading.Temperature == 0 {
		t.Error("Temperature is zero")
	}
}

func TestFetchWeather_NotFound(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		_ = json.NewEncoder(w).Encode(map[string]string{"cod": "404", "message": "city not found"})
	}))
	defer srv.Close()

	ctx := context.Background()
	_, err := NewClient(srv.URL).FetchWeather(ctx, "Atlantis", "shard-0")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "city not found") {
		t.Errorf("error %q should contain 'city not found'", err.Error())
	}
}

func TestFetchWeather_Timeout(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(2 * time.Second)
		_ = json.NewEncoder(w).Encode(moscowOWM())
	}))
	defer srv.Close()

	ctx := context.Background()
	_, err := NewClientWithTimeout(srv.URL, 500*time.Millisecond).FetchWeather(ctx, "Moscow", "shard-0")
	if err == nil {
		t.Fatal("expected timeout error, got nil")
	}
	errStr := err.Error()
	if !strings.Contains(errStr, "context") && !strings.Contains(errStr, "timeout") &&
		!strings.Contains(errStr, "deadline") && !strings.Contains(errStr, "Timeout") {
		t.Errorf("error %q does not look like a timeout/context error", errStr)
	}
}

func TestFetchBatch_Success(t *testing.T) {
	london := moscowOWM()
	london.ID = 2643743
	london.Name = "London"
	london.Sys.Country = "GB"

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode([]OWMResponse{moscowOWM(), london})
	}))
	defer srv.Close()

	ctx := context.Background()
	readings, errs := NewClient(srv.URL).FetchBatch(ctx, []string{"Moscow", "London"}, "shard-0")
	if len(errs) > 0 {
		t.Fatalf("unexpected errors: %v", errs)
	}
	if len(readings) != 2 {
		t.Fatalf("expected 2 readings, got %d", len(readings))
	}
}
