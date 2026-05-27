package api

import "time"

// WeatherReading — одна запись о погоде, полученная от мок-сервера.
type WeatherReading struct {
	CityName    string    `json:"city"`
	Country     string    `json:"country"`
	Lat         float64   `json:"lat"`
	Lon         float64   `json:"lon"`
	Temperature float64   `json:"temperature"` // °C
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
	CityName     string    `json:"city"`
	WindowStart  time.Time `json:"window_start"`
	WindowEnd    time.Time `json:"window_end"`
	Count        int       `json:"count"`
	AvgTemp      float64   `json:"avg_temp"`
	MinTemp      float64   `json:"min_temp"`
	MaxTemp      float64   `json:"max_temp"`
	AvgHumidity  float64   `json:"avg_humidity"`
	AvgPressure  float64   `json:"avg_pressure"`
	AvgWindSpeed float64   `json:"avg_wind_speed"`
	ShardID      string    `json:"shard_id"`
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
