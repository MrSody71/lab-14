package metrics

import (
	"log/slog"
	"sync/atomic"
	"time"
)

// Collector собирает простые счётчики производительности.
type Collector struct {
	fetchCount   atomic.Int64
	fetchErrors  atomic.Int64
	publishCount atomic.Int64
	startTime    time.Time
	logger       *slog.Logger
}

func New(logger *slog.Logger) *Collector {
	return &Collector{startTime: time.Now(), logger: logger}
}

func (c *Collector) IncFetch()      { c.fetchCount.Add(1) }
func (c *Collector) IncFetchError() { c.fetchErrors.Add(1) }
func (c *Collector) IncPublish()    { c.publishCount.Add(1) }

func (c *Collector) Log() {
	uptime := time.Since(c.startTime).Round(time.Second)
	c.logger.Info("metrics snapshot",
		"uptime", uptime,
		"fetches_total", c.fetchCount.Load(),
		"fetch_errors", c.fetchErrors.Load(),
		"publishes_total", c.publishCount.Load(),
	)
}
