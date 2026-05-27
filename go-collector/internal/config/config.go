package config

import (
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	MockOWMURL      string
	Cities          []string
	PollInterval    time.Duration
	WindowSize      time.Duration
	KafkaBrokers    []string
	KafkaTopic      string
	NATSUrl         string
	NATSSubject     string
	EtcdEndpoints   []string
	ShardID         string
	TotalShards     int
	ArrowFlightAddr string
	BatchSize       int
	ShutdownTimeout time.Duration
}

func Load() *Config {
	return &Config{
		MockOWMURL: getEnv("OWM_MOCK_URL", "http://localhost:8081"),
		Cities: strings.Split(getEnv("CITIES",
			"Moscow,Saint-Petersburg,Novosibirsk,Yekaterinburg,Kazan,Stockholm,Berlin,London,New-York,Tokyo"), ","),
		PollInterval:    getDuration("POLL_INTERVAL_SEC", 10) * time.Second,
		WindowSize:      getDuration("WINDOW_SIZE_SEC", 60) * time.Second,
		KafkaBrokers:    strings.Split(getEnv("KAFKA_BROKERS", "localhost:9092"), ","),
		KafkaTopic:      getEnv("KAFKA_TOPIC", "weather.raw"),
		NATSUrl:         getEnv("NATS_URL", "nats://localhost:4222"),
		NATSSubject:     getEnv("NATS_SUBJECT", "weather.raw"),
		EtcdEndpoints:   strings.Split(getEnv("ETCD_ENDPOINTS", "localhost:2379"), ","),
		ShardID:         getEnv("SHARD_ID", "shard-0"),
		TotalShards:     getInt("TOTAL_SHARDS", 1),
		ArrowFlightAddr: getEnv("ARROW_FLIGHT_ADDR", "localhost:8815"),
		BatchSize:       getInt("BATCH_SIZE", 50),
		ShutdownTimeout: getDuration("SHUTDOWN_TIMEOUT_SEC", 15) * time.Second,
	}
}

func getEnv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func getInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return def
}

func getDuration(key string, defSec int64) time.Duration {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.ParseInt(v, 10, 64); err == nil {
			return time.Duration(i)
		}
	}
	return time.Duration(defSec)
}
