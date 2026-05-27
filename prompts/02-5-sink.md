Прочитай CLAUDE.md.

Реализуй sink — публикацию агрегатов в Kafka (Redpanda) и NATS JetStream.

Добавь зависимости в go-collector/go.mod:
  go get github.com/IBM/sarama@v1.43.3
  go get github.com/nats-io/nats.go@v1.37.0

=== go-collector/internal/sink/kafka.go ===

package sink

import (
    "context"
    "encoding/json"
    "fmt"
    "log/slog"

    "github.com/IBM/sarama"
    "github.com/<USERNAME>/weather-pipeline/go-collector/internal/api"
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

=== go-collector/internal/sink/nats.go ===

package sink

import (
    "context"
    "encoding/json"
    "fmt"
    "log/slog"

    "github.com/nats-io/nats.go"
    "github.com/<USERNAME>/weather-pipeline/go-collector/internal/api"
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

=== go-collector/internal/sink/fanout.go ===

package sink

import (
    "context"
    "log/slog"

    "github.com/<USERNAME>/weather-pipeline/go-collector/internal/api"
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

Тесты для sink — только mock-тесты, без реальных брокеров:

=== go-collector/internal/sink/sink_test.go ===

TestFanout_NilSinks:
  Создать Fanout{kafka:nil, natsSk:nil}.
  Отправить 1 агрегат в ch, вызвать Run с быстро-отменяемым ctx.
  Не должно быть паники.

TestKafkaSink_MarshalError (unit, без брокера):
  Создать KafkaSink напрямую (без NewKafkaSink), подставив nil-producer.
  Передать агрегат с невалидным полем (этот тест показывает, что
  json.Marshal не фейлится на нормальной структуре — просто проверь
  что json.Marshal(WindowAggregate{CityName:"test"}) == nil error).

ПРОВЕРКА:
  go build ./go-collector/... 2>&1 && echo "BUILD OK"
  go test ./go-collector/internal/sink/... -v -count=1 2>&1

prompts/02-5-sink.md — этот промт целиком.
