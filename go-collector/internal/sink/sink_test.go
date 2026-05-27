package sink

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"testing"
	"time"

	"github.com/MrSody71/weather-pipeline/go-collector/internal/api"
)

func testLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(os.Stdout, nil))
}

func testAggregate(city string) api.WindowAggregate {
	now := time.Now().UTC()
	return api.WindowAggregate{
		CityName:    city,
		WindowStart: now.Add(-10 * time.Second),
		WindowEnd:   now,
		Count:       5,
		AvgTemp:     15.5,
		MinTemp:     12.0,
		MaxTemp:     18.0,
		AvgHumidity: 65.0,
		AvgPressure: 1013.0,
		ShardID:     "shard-0",
	}
}

func TestFanout_NilSinks(t *testing.T) {
	f := NewFanout(nil, nil, testLogger())

	ch := make(chan api.WindowAggregate, 1)
	ch <- testAggregate("TestCity")

	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	// Must not panic.
	done := make(chan struct{})
	go func() {
		defer close(done)
		f.Run(ctx, ch)
	}()

	select {
	case <-done:
	case <-time.After(200 * time.Millisecond):
		t.Fatal("Fanout.Run did not return after ctx cancel")
	}
}

func TestKafkaSink_MarshalError(t *testing.T) {
	agg := api.WindowAggregate{CityName: "test"}
	data, err := json.Marshal(agg)
	if err != nil {
		t.Fatalf("json.Marshal(WindowAggregate) returned unexpected error: %v", err)
	}
	if len(data) == 0 {
		t.Fatal("marshalled data is empty")
	}
}
