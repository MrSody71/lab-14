package internal

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
)

// owmMain is the "main" block in the OWM response.
type owmMain struct {
	Temp      float64 `json:"temp"`
	FeelsLike float64 `json:"feels_like"`
	TempMin   float64 `json:"temp_min"`
	TempMax   float64 `json:"temp_max"`
	Pressure  int     `json:"pressure"`
	Humidity  int     `json:"humidity"`
}

type owmWind struct {
	Speed float64 `json:"speed"`
	Deg   int     `json:"deg"`
}

type owmClouds struct {
	All int `json:"all"`
}

type owmWeatherItem struct {
	Description string `json:"description"`
	Icon        string `json:"icon"`
}

type owmCoord struct {
	Lat float64 `json:"lat"`
	Lon float64 `json:"lon"`
}

type owmSys struct {
	Country string `json:"country"`
}

type owmResponse struct {
	ID      int              `json:"id"`
	Name    string           `json:"name"`
	Dt      int64            `json:"dt"`
	Main    owmMain          `json:"main"`
	Wind    owmWind          `json:"wind"`
	Clouds  owmClouds        `json:"clouds"`
	Weather []owmWeatherItem `json:"weather"`
	Coord   owmCoord         `json:"coord"`
	Sys     owmSys           `json:"sys"`
}

func toOwmResponse(d WeatherData, metric bool) owmResponse {
	temp := d.Temperature
	feelsLike := d.FeelsLike
	tempMin := d.TempMin
	tempMax := d.TempMax
	if metric {
		temp -= 273.15
		feelsLike -= 273.15
		tempMin -= 273.15
		tempMax -= 273.15
	}
	return owmResponse{
		ID:   d.CityID,
		Name: d.CityName,
		Dt:   d.Timestamp,
		Main: owmMain{
			Temp:      temp,
			FeelsLike: feelsLike,
			TempMin:   tempMin,
			TempMax:   tempMax,
			Pressure:  d.Pressure,
			Humidity:  d.Humidity,
		},
		Wind:    owmWind{Speed: d.WindSpeed, Deg: d.WindDeg},
		Clouds:  owmClouds{All: d.CloudsAll},
		Weather: []owmWeatherItem{{Description: d.Description, Icon: d.Icon}},
		Coord:   owmCoord{Lat: d.Lat, Lon: d.Lon},
		Sys:     owmSys{Country: d.Country},
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// HealthHandler handles GET /health.
func HealthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "cities": 10})
}

// WeatherHandler handles GET /data/2.5/weather.
func WeatherHandler(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	cityName := q.Get("q")
	if cityName == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"cod": "400", "message": "city name required"})
		return
	}

	// Optional artificial delay (max 2000 ms).
	if delayStr := q.Get("delay"); delayStr != "" {
		if ms, err := strconv.Atoi(delayStr); err == nil && ms > 0 {
			if ms > 2000 {
				ms = 2000
			}
			time.Sleep(time.Duration(ms) * time.Millisecond)
		}
	}

	data, err := GenerateForCity(cityName)
	if err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"cod": "404", "message": "city not found"})
		return
	}

	metric := strings.EqualFold(q.Get("units"), "metric")
	writeJSON(w, http.StatusOK, toOwmResponse(data, metric))
}

// BatchHandler handles GET /batch?cities=Moscow,London,Tokyo&units=metric.
func BatchHandler(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	citiesParam := q.Get("cities")
	if citiesParam == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "cities parameter required"})
		return
	}
	metric := strings.EqualFold(q.Get("units"), "metric")

	names := strings.Split(citiesParam, ",")
	results := make([]owmResponse, len(names))
	var wg sync.WaitGroup

	for i, name := range names {
		wg.Add(1)
		go func(idx int, cityName string) {
			defer wg.Done()
			cityName = strings.TrimSpace(cityName)
			data, err := GenerateForCity(cityName)
			if err != nil {
				// Return a zero-value response for unknown cities.
				return
			}
			results[idx] = toOwmResponse(data, metric)
		}(i, name)
	}
	wg.Wait()

	writeJSON(w, http.StatusOK, results)
}
