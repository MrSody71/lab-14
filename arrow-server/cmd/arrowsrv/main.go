package main

import (
	"encoding/json"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/IBM/sarama"
	"github.com/apache/arrow/go/v17/arrow/flight"
	arrinternal "github.com/MrSody71/weather-pipeline/arrow-server/internal"
)

// windowAggregate mirrors go-collector/internal/api.WindowAggregate for JSON decoding.
type windowAggregate struct {
	CityName     string    `json:"city"`
	WindowStart  time.Time `json:"window_start"`
	WindowEnd    time.Time `json:"window_end"`
	Count        int32     `json:"count"`
	AvgTemp      float64   `json:"avg_temp"`
	MinTemp      float64   `json:"min_temp"`
	MaxTemp      float64   `json:"max_temp"`
	AvgHumidity  float64   `json:"avg_humidity"`
	AvgPressure  float64   `json:"avg_pressure"`
	AvgWindSpeed float64   `json:"avg_wind_speed"`
	ShardID      string    `json:"shard_id"`
}

func convertToRecord(agg windowAggregate) arrinternal.AggregateRecord {
	return arrinternal.AggregateRecord{
		City:         agg.CityName,
		WindowStart:  agg.WindowStart,
		WindowEnd:    agg.WindowEnd,
		Count:        agg.Count,
		AvgTemp:      agg.AvgTemp,
		MinTemp:      agg.MinTemp,
		MaxTemp:      agg.MaxTemp,
		AvgHumidity:  agg.AvgHumidity,
		AvgPressure:  agg.AvgPressure,
		AvgWindSpeed: agg.AvgWindSpeed,
		ShardID:      agg.ShardID,
	}
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	addr := os.Getenv("ARROW_FLIGHT_ADDR")
	if addr == "" {
		addr = ":8815"
	}

	maxRecords := 1000
	if v := os.Getenv("ARROW_MAX_RECORDS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			maxRecords = n
		}
	}

	kafkaBrokers := strings.Split(os.Getenv("KAFKA_BROKERS"), ",")
	if len(kafkaBrokers) == 1 && kafkaBrokers[0] == "" {
		kafkaBrokers = []string{"localhost:9092"}
	}
	kafkaTopic := os.Getenv("KAFKA_TOPIC")
	if kafkaTopic == "" {
		kafkaTopic = "weather.raw"
	}

	store := arrinternal.NewStore(maxRecords)
	flightSvc := arrinternal.NewFlightServer(store)

	srv := flight.NewFlightServer()
	if err := srv.Init(addr); err != nil {
		logger.Error("flight server init failed", "err", err)
		os.Exit(1)
	}
	srv.RegisterFlightService(flightSvc)
	srv.SetShutdownOnSignals(os.Interrupt, syscall.SIGTERM)

	logger.Info("arrow-server starting", "addr", addr, "max_records", maxRecords)

	// Kafka consumer goroutine.
	go func() {
		consumer, err := sarama.NewConsumer(kafkaBrokers, nil)
		if err != nil {
			logger.Warn("kafka consumer unavailable", "err", err)
			return
		}
		defer consumer.Close()

		partConsumer, err := consumer.ConsumePartition(kafkaTopic, 0, sarama.OffsetNewest)
		if err != nil {
			logger.Warn("kafka consume partition failed", "err", err)
			return
		}
		defer partConsumer.Close()

		logger.Info("kafka consumer started", "topic", kafkaTopic)
		for msg := range partConsumer.Messages() {
			var agg windowAggregate
			if err := json.Unmarshal(msg.Value, &agg); err != nil {
				logger.Warn("kafka message unmarshal failed", "err", err)
				continue
			}
			store.Add(convertToRecord(agg))
		}
	}()

	if err := srv.Serve(); err != nil {
		logger.Error("flight server error", "err", err)
		os.Exit(1)
	}
	logger.Info("arrow-server stopped")
}
