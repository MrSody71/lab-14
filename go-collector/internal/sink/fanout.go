package sink

import (
	"context"
	"log/slog"

	"github.com/MrSody71/weather-pipeline/go-collector/internal/api"
)

// Fanout читает из одного канала и параллельно отправляет
// в Kafka и NATS. Если один из sink недоступен — логирует ошибку,
// но продолжает работу.
type Fanout struct {
	kafka  *KafkaSink
	natsSk *NATSSink
	logger *slog.Logger
}

func NewFanout(kafka *KafkaSink, nats *NATSSink,
	logger *slog.Logger) *Fanout {
	return &Fanout{kafka: kafka, natsSk: nats, logger: logger}
}

func (f *Fanout) Run(ctx context.Context, ch <-chan api.WindowAggregate) {
	for {
		select {
		case <-ctx.Done():
			return
		case agg, ok := <-ch:
			if !ok {
				return
			}
			if f.kafka != nil {
				if err := f.kafka.PublishAggregate(agg); err != nil {
					f.logger.Error("kafka fanout error", "err", err)
				}
			}
			if f.natsSk != nil {
				if err := f.natsSk.PublishAggregate(agg); err != nil {
					f.logger.Error("nats fanout error", "err", err)
				}
			}
		}
	}
}
