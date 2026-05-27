package window

import (
	"context"
	"log/slog"
	"math"
	"sync"
	"time"

	"github.com/MrSody71/weather-pipeline/go-collector/internal/api"
)

// cityWindow накапливает показания для одного города в текущем окне.
type cityWindow struct {
	readings []api.WeatherReading
	start    time.Time
}

// TumblingWindow принимает WeatherReading из inputCh,
// накапливает их по городам, и каждые windowSize публикует
// WindowAggregate в output-канал.
type TumblingWindow struct {
	windowSize time.Duration
	windows    map[string]*cityWindow
	mu         sync.Mutex
	logger     *slog.Logger
}

func NewTumblingWindow(size time.Duration, logger *slog.Logger) *TumblingWindow {
	return &TumblingWindow{
		windowSize: size,
		windows:    make(map[string]*cityWindow),
		logger:     logger,
	}
}

// Run читает из inputCh, накапливает данные, каждые windowSize
// флашит агрегаты в outputCh. Завершается когда ctx отменён.
func (tw *TumblingWindow) Run(ctx context.Context,
	inputCh <-chan api.WeatherReading,
	outputCh chan<- api.WindowAggregate) {

	ticker := time.NewTicker(tw.windowSize)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			tw.flush(outputCh)
			return

		case reading, ok := <-inputCh:
			if !ok {
				tw.flush(outputCh)
				return
			}
			tw.add(reading)

		case <-ticker.C:
			tw.flush(outputCh)
		}
	}
}

// add добавляет показание в окно города.
func (tw *TumblingWindow) add(r api.WeatherReading) {
	tw.mu.Lock()
	defer tw.mu.Unlock()

	w, ok := tw.windows[r.CityName]
	if !ok {
		w = &cityWindow{start: time.Now().UTC()}
		tw.windows[r.CityName] = w
	}
	w.readings = append(w.readings, r)
}

// flush вычисляет агрегаты для всех городов и сбрасывает окна.
func (tw *TumblingWindow) flush(outputCh chan<- api.WindowAggregate) {
	tw.mu.Lock()
	defer tw.mu.Unlock()

	if len(tw.windows) == 0 {
		return
	}

	now := time.Now().UTC()
	for city, w := range tw.windows {
		if len(w.readings) == 0 {
			continue
		}
		agg := aggregate(city, w.start, now, w.readings)
		tw.logger.Info("window flushed",
			"city", city,
			"count", agg.Count,
			"avg_temp", agg.AvgTemp)
		select {
		case outputCh <- agg:
		default:
			tw.logger.Warn("output channel full, dropping aggregate",
				"city", city)
		}
	}
	tw.windows = make(map[string]*cityWindow)
}

// aggregate вычисляет WindowAggregate из слайса показаний.
func aggregate(city string, start, end time.Time,
	readings []api.WeatherReading) api.WindowAggregate {

	var (
		sumTemp, sumHum, sumPres, sumWind float64
		minTemp                           = readings[0].Temperature
		maxTemp                           = readings[0].Temperature
		shardID                           = readings[0].ShardID
	)
	for _, r := range readings {
		sumTemp += r.Temperature
		sumHum += float64(r.Humidity)
		sumPres += float64(r.Pressure)
		sumWind += r.WindSpeed
		if r.Temperature < minTemp {
			minTemp = r.Temperature
		}
		if r.Temperature > maxTemp {
			maxTemp = r.Temperature
		}
	}
	n := float64(len(readings))
	return api.WindowAggregate{
		CityName:     city,
		WindowStart:  start,
		WindowEnd:    end,
		Count:        len(readings),
		AvgTemp:      round2(sumTemp / n),
		MinTemp:      minTemp,
		MaxTemp:      maxTemp,
		AvgHumidity:  round2(sumHum / n),
		AvgPressure:  round2(sumPres / n),
		AvgWindSpeed: round2(sumWind / n),
		ShardID:      shardID,
	}
}

func round2(f float64) float64 {
	return math.Round(f*100) / 100
}
