Прочитай CLAUDE.md.

Реализуй Apache Arrow Flight сервер в arrow-server/.
Сервер хранит последние агрегаты по городам в памяти и отдаёт их
Python-клиенту в формате Arrow RecordBatch через DoGet.

Добавь зависимости в arrow-server/go.mod:
  go get github.com/apache/arrow/go/v17@latest
  go get google.golang.org/grpc@v1.65.0

=== arrow-server/internal/store.go ===

package internal

import (
    "sync"
    "time"
)

// AggregateRecord — запись агрегата, которую мы храним в памяти.
type AggregateRecord struct {
    City         string
    WindowStart  time.Time
    WindowEnd    time.Time
    Count        int32
    AvgTemp      float64
    MinTemp      float64
    MaxTemp      float64
    AvgHumidity  float64
    AvgPressure  float64
    AvgWindSpeed float64
    ShardID      string
}

// Store — потокобезопасное хранилище последних агрегатов.
// Хранит последние MaxPerCity записей на город.
type Store struct {
    mu         sync.RWMutex
    records    []AggregateRecord
    maxRecords int
}

func NewStore(maxRecords int) *Store {
    return &Store{maxRecords: maxRecords}
}

// Add добавляет запись в хранилище.
// Если записей больше maxRecords — удаляет самые старые.
func (s *Store) Add(r AggregateRecord) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.records = append(s.records, r)
    if len(s.records) > s.maxRecords {
        s.records = s.records[len(s.records)-s.maxRecords:]
    }
}

// GetAll возвращает копию всех записей.
func (s *Store) GetAll() []AggregateRecord {
    s.mu.RLock()
    defer s.mu.RUnlock()
    out := make([]AggregateRecord, len(s.records))
    copy(out, s.records)
    return out
}

// GetByCity возвращает записи только для указанного города.
func (s *Store) GetByCity(city string) []AggregateRecord {
    s.mu.RLock()
    defer s.mu.RUnlock()
    var out []AggregateRecord
    for _, r := range s.records {
        if r.City == city {
            out = append(out, r)
        }
    }
    return out
}

=== arrow-server/internal/store_test.go ===

TestStore_AddAndGet:
  Добавить 3 записи для "Moscow", 2 для "London".
  GetAll() → 5 записей.
  GetByCity("Moscow") → 3.
  GetByCity("Berlin") → 0.

TestStore_MaxRecords:
  Store с maxRecords=3.
  Добавить 5 записей.
  GetAll() → ровно 3 (самые новые).

=== arrow-server/internal/flight.go ===

package internal

import (
    "context"
    "fmt"

    "github.com/apache/arrow/go/v17/arrow"
    "github.com/apache/arrow/go/v17/arrow/array"
    "github.com/apache/arrow/go/v17/arrow/flight"
    "github.com/apache/arrow/go/v17/arrow/ipc"
    "github.com/apache/arrow/go/v17/arrow/memory"
)

// WeatherSchema — Arrow-схема для агрегатов погоды.
var WeatherSchema = arrow.NewSchema([]arrow.Field{
    {Name: "city",          Type: arrow.BinaryTypes.String},
    {Name: "window_start",  Type: arrow.FixedWidthTypes.Timestamp_s},
    {Name: "window_end",    Type: arrow.FixedWidthTypes.Timestamp_s},
    {Name: "count",         Type: arrow.PrimitiveTypes.Int32},
    {Name: "avg_temp",      Type: arrow.PrimitiveTypes.Float64},
    {Name: "min_temp",      Type: arrow.PrimitiveTypes.Float64},
    {Name: "max_temp",      Type: arrow.PrimitiveTypes.Float64},
    {Name: "avg_humidity",  Type: arrow.PrimitiveTypes.Float64},
    {Name: "avg_pressure",  Type: arrow.PrimitiveTypes.Float64},
    {Name: "avg_wind_speed",Type: arrow.PrimitiveTypes.Float64},
    {Name: "shard_id",      Type: arrow.BinaryTypes.String},
}, nil)

// RecordsToArrow конвертирует []AggregateRecord в Arrow RecordBatch.
func RecordsToArrow(records []AggregateRecord) (arrow.Record, error) { ... }

// FlightServer реализует Arrow Flight DoGet.
type FlightServer struct {
    flight.BaseFlightServer
    store *Store
}

func NewFlightServer(store *Store) *FlightServer { ... }

// GetFlightInfo возвращает информацию о доступных потоках.
func (s *FlightServer) GetFlightInfo(ctx, req) (*FlightInfo, error) { ... }

// DoGet отдаёт RecordBatch по тикету.
// Ticket = "all" → все записи, иначе → фильтр по городу.
func (s *FlightServer) DoGet(ticket, stream) error { ... }

=== arrow-server/internal/flight_test.go ===

TestRecordsToArrow_Empty:
  RecordsToArrow([]) не возвращает ошибку,
  record.NumRows() == 0,
  record.Schema().NumFields() == 11.

TestRecordsToArrow_Data:
  Создать 2 AggregateRecord (Moscow, London).
  RecordsToArrow → record.NumRows() == 2.
  Колонка "city" содержит ["Moscow","London"].

=== arrow-server/cmd/arrowsrv/main.go ===

Замени заглушку:

1. Загрузить адрес из env ARROW_FLIGHT_ADDR (default ":8815")
2. Загрузить ARROW_MAX_RECORDS (default 1000)
3. Загрузить KAFKA_BROKERS и KAFKA_TOPIC (default "weather.raw")
4. Создать internal.NewStore(maxRecords)
5. Создать FlightServer
6. Запустить Flight сервер на указанном адресе
7. В отдельной горутине — Kafka consumer, который читает
   WindowAggregate JSON из топика weather.raw и кладёт в Store через Add.
   Если Kafka недоступна — логировать warn и продолжить без consumer.
8. Graceful shutdown по SIGINT через flight.Server.SetShutdownOnSignals.

Добавь в arrow-server/go.mod:
  go get github.com/IBM/sarama@v1.43.3
  (apache/arrow уже добавлен)

ПРОВЕРКА:
  go build ./arrow-server/... 2>&1 && echo "BUILD OK"
  go test ./arrow-server/internal/... -v -count=1 2>&1

4 теста зелёных.

prompts/03-1-arrow-server.md — этот промт целиком.
