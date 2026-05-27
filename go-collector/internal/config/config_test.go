package config

import (
	"strings"
	"testing"
	"time"
)

func TestLoadDefaults(t *testing.T) {
	cfg := Load()
	if !strings.Contains(cfg.MockOWMURL, "localhost:8081") {
		t.Errorf("MockOWMURL = %q, want to contain localhost:8081", cfg.MockOWMURL)
	}
	if len(cfg.Cities) != 10 {
		t.Errorf("len(Cities) = %d, want 10", len(cfg.Cities))
	}
	if cfg.PollInterval != 10*time.Second {
		t.Errorf("PollInterval = %v, want 10s", cfg.PollInterval)
	}
}

func TestLoadFromEnv(t *testing.T) {
	t.Setenv("TOTAL_SHARDS", "3")
	cfg := Load()
	if cfg.TotalShards != 3 {
		t.Errorf("TotalShards = %d, want 3", cfg.TotalShards)
	}
}
