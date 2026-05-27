package internal

import (
	"fmt"
	"math/rand"
	"strings"
	"time"
)

// rng is the package-level random source; initialised by Init (or lazily here).
var rng = rand.New(rand.NewSource(time.Now().UnixNano()))

// Init seeds the package random source with the given value for reproducibility.
func Init(seed int64) {
	rng = rand.New(rand.NewSource(seed))
}

// WeatherData holds raw generated weather values (temperatures in Kelvin).
type WeatherData struct {
	CityID      int     `json:"id"`
	CityName    string  `json:"name"`
	Timestamp   int64   `json:"dt"`
	Temperature float64 `json:"temp"`
	FeelsLike   float64 `json:"feels_like"`
	TempMin     float64 `json:"temp_min"`
	TempMax     float64 `json:"temp_max"`
	Pressure    int     `json:"pressure"`
	Humidity    int     `json:"humidity"`
	WindSpeed   float64 `json:"wind_speed"`
	WindDeg     int     `json:"wind_deg"`
	CloudsAll   int     `json:"clouds_all"`
	Description string  `json:"description"`
	Icon        string  `json:"icon"`
	Country     string  `json:"country"`
	Lat         float64 `json:"lat"`
	Lon         float64 `json:"lon"`
}

// CityMeta holds static metadata for a city.
type CityMeta struct {
	ID       int
	Country  string
	Lat      float64
	Lon      float64
	BaseTemp float64 // Kelvin
}

var cities = map[string]CityMeta{
	"moscow":           {ID: 524901, Country: "RU", Lat: 55.75, Lon: 37.62, BaseTemp: 278},
	"saint-petersburg": {ID: 498817, Country: "RU", Lat: 59.95, Lon: 30.32, BaseTemp: 275},
	"novosibirsk":      {ID: 1496747, Country: "RU", Lat: 54.99, Lon: 82.90, BaseTemp: 273},
	"yekaterinburg":    {ID: 1486209, Country: "RU", Lat: 56.85, Lon: 60.61, BaseTemp: 274},
	"kazan":            {ID: 551487, Country: "RU", Lat: 55.79, Lon: 49.12, BaseTemp: 276},
	"stockholm":        {ID: 2673730, Country: "SE", Lat: 59.33, Lon: 18.07, BaseTemp: 280},
	"berlin":           {ID: 2950159, Country: "DE", Lat: 52.52, Lon: 13.40, BaseTemp: 282},
	"london":           {ID: 2643743, Country: "GB", Lat: 51.51, Lon: -0.13, BaseTemp: 284},
	"new-york":         {ID: 5128581, Country: "US", Lat: 40.71, Lon: -74.01, BaseTemp: 288},
	"tokyo":            {ID: 1850147, Country: "JP", Lat: 35.69, Lon: 139.69, BaseTemp: 290},
}

var descriptions = []string{
	"clear sky", "few clouds", "scattered clouds", "broken clouds",
	"shower rain", "rain", "thunderstorm", "snow", "mist",
}

var iconMap = map[string]string{
	"clear sky":      "01d",
	"few clouds":     "02d",
	"scattered clouds": "03d",
}

func descriptionToIcon(desc string) string {
	if icon, ok := iconMap[desc]; ok {
		return icon
	}
	return "04d"
}

// Generate creates a WeatherData for the given city name and base temperature (Kelvin).
func Generate(city string, meta CityMeta) WeatherData {
	temp := meta.BaseTemp + rng.Float64()*6 - 3
	feelsLike := temp - 2 + rng.Float64()*2 - 1
	tempMin := temp - rng.Float64()*2
	tempMax := temp + rng.Float64()*2
	pressure := 1000 + rng.Intn(31)
	humidity := 40 + rng.Intn(56)
	windSpeed := float64(int(rng.Float64()*150)) / 10.0
	windDeg := rng.Intn(361)
	cloudsAll := rng.Intn(101)
	desc := descriptions[rng.Intn(len(descriptions))]

	return WeatherData{
		CityID:      meta.ID,
		CityName:    city,
		Timestamp:   time.Now().Unix(),
		Temperature: temp,
		FeelsLike:   feelsLike,
		TempMin:     tempMin,
		TempMax:     tempMax,
		Pressure:    pressure,
		Humidity:    humidity,
		WindSpeed:   windSpeed,
		WindDeg:     windDeg,
		CloudsAll:   cloudsAll,
		Description: desc,
		Icon:        descriptionToIcon(desc),
		Country:     meta.Country,
		Lat:         meta.Lat,
		Lon:         meta.Lon,
	}
}

// GenerateForCity looks up the city (case-insensitive) and generates WeatherData for it.
func GenerateForCity(cityName string) (WeatherData, error) {
	key := strings.ToLower(cityName)
	meta, ok := cities[key]
	if !ok {
		return WeatherData{}, fmt.Errorf("city not found: %s", cityName)
	}
	// Use the original casing from the map key (capitalised display name).
	displayName := cityName
	return Generate(displayName, meta), nil
}
