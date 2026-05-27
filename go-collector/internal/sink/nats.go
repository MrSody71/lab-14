package sink

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"

	"github.com/nats-io/nats.go"
	"github.com/MrSody71/weather-pipeline/go-collector/internal/api"
)

type NATSSink struct {
	nc      *nats.Conn
	js      nats.JetStreamContext
	subject string
	logger  *slog.Logger
}

func NewNATSSink(url, subject string, logger *slog.Logger) (*NATSSink, error) {
	nc, err := nats.Connect(url)
	if err != nil {
		return nil, fmt.Errorf("connect nats: %w", err)
	}
	js, err := nc.JetStream()
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("jetstream context: %w", err)
	}
	// Создать stream если не существует
	_, err = js.AddStream(&nats.StreamConfig{
		Name:     "WEATHER",
		Subjects: []string{"weather.>"},
	})
	if err != nil && err != nats.ErrStreamNameAlreadyInUse {
		nc.Close()
		return nil, fmt.Errorf("create stream: %w", err)
	}
	return &NATSSink{nc: nc, js: js, subject: subject, logger: logger}, nil
}

// PublishAggregate публикует WindowAggregate в NATS JetStream.
func (n *NATSSink) PublishAggregate(agg api.WindowAggregate) error {
	data, err := json.Marshal(agg)
	if err != nil {
		return fmt.Errorf("marshal: %w", err)
	}
	subj := fmt.Sprintf("%s.%s", n.subject, agg.CityName)
	ack, err := n.js.Publish(subj, data)
	if err != nil {
		return fmt.Errorf("nats publish: %w", err)
	}
	n.logger.Debug("published to nats",
		"subject", subj,
		"seq", ack.Sequence)
	return nil
}

// Run читает агрегаты из ch и публикует. Завершается по ctx.
func (n *NATSSink) Run(ctx context.Context, ch <-chan api.WindowAggregate) {
	for {
		select {
		case <-ctx.Done():
			return
		case agg, ok := <-ch:
			if !ok {
				return
			}
			if err := n.PublishAggregate(agg); err != nil {
				n.logger.Error("nats publish failed",
					"city", agg.CityName, "err", err)
			}
		}
	}
}

func (n *NATSSink) Close() {
	n.nc.Close()
}
