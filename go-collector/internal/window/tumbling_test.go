package window

import (
	"context"
	"log/slog"
	"os"
	"testing"
	"time"

	"github.com/MrSody71/weather-pipeline/go-collector/internal/api"
)

func makeReading(city string, temp float64, humidity int) api.WeatherReading {
	return api.WeatherReading{
		CityName:    city,
		Temperature: temp,
		Humidity:    humidity,
		Pressure:    1013,
		WindSpeed:   3.0,
		ShardID:     "shard-0",
		CollectedAt: time.Now().UTC(),
	}
}

func TestAggregate_Basic(t *testing.T) {
	start := time.Now().UTC()
	end := start.Add(10 * time.Second)
	readings := []api.WeatherReading{
		makeReading("Moscow", 10.0, 50),
		makeReading("Moscow", 20.0, 60),
		makeReading("Moscow", 30.0, 70),
	}

	agg := aggregate("Moscow", start, end, readings)

	if agg.Count != 3 {
		t.Errorf("Count = %d, want 3", agg.Count)
	}
	if agg.AvgTemp != 20.0 {
		t.Errorf("AvgTemp = %f, want 20.0", agg.AvgTemp)
	}
	if agg.MinTemp != 10.0 {
		t.Errorf("MinTemp = %f, want 10.0", agg.MinTemp)
	}
	if agg.MaxTemp != 30.0 {
		t.Errorf("MaxTemp = %f, want 30.0", agg.MaxTemp)
	}
	if agg.AvgHumidity != 60.0 {
		t.Errorf("AvgHumidity = %f, want 60.0", agg.AvgHumidity)
	}
}

func TestTumblingWindow_Flush(t *testing.T) {
	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	tw := NewTumblingWindow(50*time.Millisecond, logger)

	inputCh := make(chan api.WeatherReading, 10)
	outputCh := make(chan api.WindowAggregate, 10)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go tw.Run(ctx, inputCh, outputCh)

	inputCh <- makeReading("London", 15.0, 65)
	inputCh <- makeReading("London", 17.0, 70)

	// Wait for at least one tick to fire and flush.
	time.Sleep(120 * time.Millisecond)

	if len(outputCh) == 0 {
		t.Fatal("expected at least one aggregate in outputCh, got none")
	}

	agg := <-outputCh
	if agg.Count < 2 {
		t.Errorf("Count = %d, want >= 2", agg.Count)
	}
}

func TestTumblingWindow_MultiCity(t *testing.T) {
	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	tw := NewTumblingWindow(50*time.Millisecond, logger)

	inputCh := make(chan api.WeatherReading, 10)
	outputCh := make(chan api.WindowAggregate, 10)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go tw.Run(ctx, inputCh, outputCh)

	inputCh <- makeReading("Berlin", 12.0, 55)
	inputCh <- makeReading("Berlin", 14.0, 58)
	inputCh <- makeReading("Tokyo", 22.0, 80)
	inputCh <- makeReading("Tokyo", 24.0, 82)

	// Wait for flush.
	time.Sleep(120 * time.Millisecond)

	got := len(outputCh)
	if got < 2 {
		t.Errorf("expected at least 2 aggregates, got %d", got)
	}

	cities := make(map[string]bool)
	for i := 0; i < got; i++ {
		agg := <-outputCh
		cities[agg.CityName] = true
	}
	if !cities["Berlin"] {
		t.Error("missing aggregate for Berlin")
	}
	if !cities["Tokyo"] {
		t.Error("missing aggregate for Tokyo")
	}
}
