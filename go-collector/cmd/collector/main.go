package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/MrSody71/weather-pipeline/go-collector/internal/api"
	"github.com/MrSody71/weather-pipeline/go-collector/internal/config"
	"github.com/MrSody71/weather-pipeline/go-collector/internal/metrics"
	"github.com/MrSody71/weather-pipeline/go-collector/internal/shard"
	"github.com/MrSody71/weather-pipeline/go-collector/internal/sink"
	"github.com/MrSody71/weather-pipeline/go-collector/internal/window"
)

func main() {
	cfg := config.Load()

	// Настроить slog (JSON, уровень из LOG_LEVEL).
	logLevel := slog.LevelInfo
	if v := os.Getenv("LOG_LEVEL"); v != "" {
		switch v {
		case "debug":
			logLevel = slog.LevelDebug
		case "warn":
			logLevel = slog.LevelWarn
		case "error":
			logLevel = slog.LevelError
		}
	}
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: logLevel}))
	slog.SetDefault(logger)

	logger.Info("go-collector starting",
		"shard_id", cfg.ShardID,
		"poll_interval", cfg.PollInterval,
		"window_size", cfg.WindowSize,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// --- API client ---
	client := api.NewClient(cfg.MockOWMURL)

	// --- Shard manager ---
	var shardManager *shard.Manager
	sm, err := shard.NewManager(cfg.EtcdEndpoints, cfg.ShardID, cfg.Cities, logger)
	if err != nil {
		logger.Warn("etcd unavailable, using all cities", "err", err)
	} else {
		shardManager = sm
	}

	// --- Window ---
	tw := window.NewTumblingWindow(cfg.WindowSize, logger)

	// --- Kafka sink ---
	var kafkaSink *sink.KafkaSink
	ks, err := sink.NewKafkaSink(cfg.KafkaBrokers, cfg.KafkaTopic, logger)
	if err != nil {
		logger.Warn("kafka unavailable", "err", err)
	} else {
		kafkaSink = ks
	}

	// --- NATS sink ---
	var natsSink *sink.NATSSink
	ns, err := sink.NewNATSSink(cfg.NATSUrl, cfg.NATSSubject, logger)
	if err != nil {
		logger.Warn("nats unavailable", "err", err)
	} else {
		natsSink = ns
	}

	// --- Fanout ---
	fanout := sink.NewFanout(kafkaSink, natsSink, logger)

	// --- Metrics ---
	met := metrics.New(logger)

	// --- Channels ---
	readingsCh := make(chan api.WeatherReading, 100)
	aggregatesCh := make(chan api.WindowAggregate, 50)

	// --- Goroutines ---
	if shardManager != nil {
		go func() {
			if err := shardManager.Register(ctx); err != nil {
				logger.Warn("shard register ended", "err", err)
			}
		}()
	}

	go tw.Run(ctx, readingsCh, aggregatesCh)
	go fanout.Run(ctx, aggregatesCh)

	// Main poll loop.
	go func() {
		ticker := time.NewTicker(cfg.PollInterval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				var cities []string
				if shardManager != nil {
					cities, err = shardManager.MyCities(ctx)
					if err != nil {
						logger.Warn("get cities failed", "err", err)
						cities = cfg.Cities
					}
				} else {
					cities = cfg.Cities
				}

				var wg sync.WaitGroup
				for _, city := range cities {
					wg.Add(1)
					go func(c string) {
						defer wg.Done()
						r, err := client.FetchWeather(ctx, c, cfg.ShardID)
						if err != nil {
							logger.Warn("fetch failed", "city", c, "err", err)
							met.IncFetchError()
							return
						}
						met.IncFetch()
						select {
						case readingsCh <- r:
						case <-ctx.Done():
						}
					}(city)
				}
				wg.Wait()
			}
		}
	}()

	// Metrics ticker.
	go func() {
		t := time.NewTicker(30 * time.Second)
		defer t.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-t.C:
				met.Log()
			}
		}
	}()

	// --- Graceful shutdown ---
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh
	logger.Info("shutdown signal received")
	cancel()

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer shutdownCancel()
	<-shutdownCtx.Done()

	logger.Info("shutdown complete")

	if kafkaSink != nil {
		_ = kafkaSink.Close()
	}
	if natsSink != nil {
		natsSink.Close()
	}
	if shardManager != nil {
		_ = shardManager.Close()
	}
}
