package sink

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"

	"github.com/IBM/sarama"
	"github.com/MrSody71/weather-pipeline/go-collector/internal/api"
)

type KafkaSink struct {
	producer sarama.SyncProducer
	topic    string
	logger   *slog.Logger
}

func NewKafkaSink(brokers []string, topic string,
	logger *slog.Logger) (*KafkaSink, error) {

	cfg := sarama.NewConfig()
	cfg.Producer.Return.Successes = true
	cfg.Producer.RequiredAcks = sarama.WaitForLocal
	cfg.Producer.Retry.Max = 3

	producer, err := sarama.NewSyncProducer(brokers, cfg)
	if err != nil {
		return nil, fmt.Errorf("create kafka producer: %w", err)
	}
	return &KafkaSink{producer: producer, topic: topic, logger: logger}, nil
}

// PublishAggregate сериализует WindowAggregate в JSON и публикует в Kafka.
// Ключ сообщения = CityName (для партиционирования по городу).
func (k *KafkaSink) PublishAggregate(agg api.WindowAggregate) error {
	data, err := json.Marshal(agg)
	if err != nil {
		return fmt.Errorf("marshal aggregate: %w", err)
	}
	msg := &sarama.ProducerMessage{
		Topic: k.topic,
		Key:   sarama.StringEncoder(agg.CityName),
		Value: sarama.ByteEncoder(data),
	}
	partition, offset, err := k.producer.SendMessage(msg)
	if err != nil {
		return fmt.Errorf("send to kafka: %w", err)
	}
	k.logger.Debug("published to kafka",
		"city", agg.CityName,
		"partition", partition,
		"offset", offset)
	return nil
}

// Run читает агрегаты из ch и публикует их. Завершается по ctx.
func (k *KafkaSink) Run(ctx context.Context, ch <-chan api.WindowAggregate) {
	for {
		select {
		case <-ctx.Done():
			return
		case agg, ok := <-ch:
			if !ok {
				return
			}
			if err := k.PublishAggregate(agg); err != nil {
				k.logger.Error("kafka publish failed",
					"city", agg.CityName, "err", err)
			}
		}
	}
}

func (k *KafkaSink) Close() error {
	return k.producer.Close()
}
