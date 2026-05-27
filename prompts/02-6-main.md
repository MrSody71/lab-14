Прочитай CLAUDE.md.

Соедини все части в главном main.go коллектора.
Это последний файл этапа — wire-up всех компонентов.

=== go-collector/internal/metrics/metrics.go ===

package metrics

import (
    "log/slog"
    "sync/atomic"
    "time"
)

// Collector собирает простые счётчики производительности.
// Без внешних зависимостей — только атомарные счётчики.
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

func (c *Collector) IncFetch()        { c.fetchCount.Add(1) }
func (c *Collector) IncFetchError()   { c.fetchErrors.Add(1) }
func (c *Collector) IncPublish()      { c.publishCount.Add(1) }

func (c *Collector) Log() {
    uptime := time.Since(c.startTime).Round(time.Second)
    c.logger.Info("metrics snapshot",
        "uptime", uptime,
        "fetches_total", c.fetchCount.Load(),
        "fetch_errors", c.fetchErrors.Load(),
        "publishes_total", c.publishCount.Load(),
    )
}

=== go-collector/cmd/collector/main.go ===

Замени заглушку на полноценный main.

Логика:

1. Загрузить config.Load()
2. Настроить slog (JSON-формат, уровень из env LOG_LEVEL, default "info")
3. Создать api.Client
4. Создать shard.Manager (если etcd недоступен — логировать warn и
   продолжить с полным списком городов, не падать)
5. Создать window.TumblingWindow
6. Создать sink.KafkaSink (если Kafka недоступна — логировать warn,
   kafkaSink = nil)
7. Создать sink.NATSSink (если NATS недоступен — логировать warn,
   natsSink = nil)
8. Создать sink.Fanout(kafkaSink, natsSink)
9. Создать metrics.Collector

Каналы:
  readingsCh := make(chan api.WeatherReading, 100)
  aggregatesCh := make(chan api.WindowAggregate, 50)

Запустить горутины:
  go shardManager.Register(ctx)          // регистрация в etcd
  go window.Run(ctx, readingsCh, aggregatesCh)  // агрегация
  go fanout.Run(ctx, aggregatesCh)       // публикация

  // Основной цикл сбора: тикер каждые cfg.PollInterval
  go func() {
      ticker := time.NewTicker(cfg.PollInterval)
      defer ticker.Stop()
      for {
          select {
          case <-ctx.Done():
              return
          case <-ticker.C:
              cities, err := shardManager.MyCities(ctx)
              if err != nil {
                  logger.Warn("get cities failed", "err", err)
                  cities = cfg.Cities
              }
              // Параллельный опрос всех городов
              var wg sync.WaitGroup
              for _, city := range cities {
                  wg.Add(1)
                  go func(c string) {
                      defer wg.Done()
                      r, err := client.FetchWeather(ctx, c, cfg.ShardID)
                      if err != nil {
                          logger.Warn("fetch failed",
                              "city", c, "err", err)
                          metrics.IncFetchError()
                          return
                      }
                      metrics.IncFetch()
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

  // Тикер метрик каждые 30 секунд
  go func() {
      t := time.NewTicker(30 * time.Second)
      defer t.Stop()
      for {
          select {
          case <-ctx.Done():
              return
          case <-t.C:
              metrics.Log()
          }
      }
  }()

Graceful shutdown:
  sigCh := make(chan os.Signal, 1)
  signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
  <-sigCh
  logger.Info("shutdown signal received")
  cancel()

  // Ждём cfg.ShutdownTimeout
  shutdownCtx, shutdownCancel := context.WithTimeout(
      context.Background(), cfg.ShutdownTimeout)
  defer shutdownCancel()

  // Дать горутинам завершиться
  <-shutdownCtx.Done()  // в реальности отслеживать через WaitGroup —
                          // упростим: просто sleep до таймаута
  logger.Info("shutdown complete")

  // Закрыть sink
  if kafkaSink != nil {
      _ = kafkaSink.Close()
  }
  if natsSink != nil {
      natsSink.Close()
  }
  if shardManager != nil {
      _ = shardManager.Close()
  }

ПРОВЕРКА:
  go build ./go-collector/... 2>&1 && echo "BUILD OK"
  go vet ./go-collector/... 2>&1

Запустить 3 секунды и убить:
  (на Linux/Mac)
  timeout 3 go run ./go-collector/cmd/collector 2>&1 || true

  (на Windows PowerShell)
  $p = Start-Process go -ArgumentList "run","./go-collector/cmd/collector" -PassThru
  Start-Sleep 3
  Stop-Process -Id $p.Id -Force
  # Посмотреть что в консоли напечаталось

Должны увидеть строки:
  "go-collector starting"
  "shard registered" или "etcd unavailable"
  "shutdown signal received"
  "shutdown complete"

prompts/02-6-main.md — этот промт целиком.
