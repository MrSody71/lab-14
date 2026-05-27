package api

import (
	"testing"
)

func TestToReading(t *testing.T) {
	owm := OWMResponse{
		ID:   524901,
		Name: "Moscow",
		Dt:   1700000000,
	}
	owm.Main.Temp = 5.5
	owm.Main.FeelsLike = 3.2
	owm.Main.TempMin = 4.0
	owm.Main.TempMax = 7.1
	owm.Main.Pressure = 1013
	owm.Main.Humidity = 75
	owm.Wind.Speed = 3.5
	owm.Wind.Deg = 180
	owm.Clouds.All = 40
	owm.Weather = []struct {
		Description string `json:"description"`
		Icon        string `json:"icon"`
	}{{Description: "few clouds", Icon: "02d"}}
	owm.Coord.Lat = 55.75
	owm.Coord.Lon = 37.62
	owm.Sys.Country = "RU"

	r := owm.ToReading("shard-0")

	if r.Temperature != owm.Main.Temp {
		t.Errorf("Temperature = %f, want %f", r.Temperature, owm.Main.Temp)
	}
	if r.ShardID != "shard-0" {
		t.Errorf("ShardID = %q, want shard-0", r.ShardID)
	}
	if r.CollectedAt.IsZero() {
		t.Error("CollectedAt is zero")
	}
}
