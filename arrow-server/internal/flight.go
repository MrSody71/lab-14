package internal

import (
	"fmt"

	"github.com/apache/arrow/go/v17/arrow"
	"github.com/apache/arrow/go/v17/arrow/array"
	"github.com/apache/arrow/go/v17/arrow/flight"
	"github.com/apache/arrow/go/v17/arrow/ipc"
	"github.com/apache/arrow/go/v17/arrow/memory"
	"golang.org/x/net/context"
)

// WeatherSchema — Arrow-схема для агрегатов погоды.
var WeatherSchema = arrow.NewSchema([]arrow.Field{
	{Name: "city", Type: arrow.BinaryTypes.String},
	{Name: "window_start", Type: arrow.FixedWidthTypes.Timestamp_s},
	{Name: "window_end", Type: arrow.FixedWidthTypes.Timestamp_s},
	{Name: "count", Type: arrow.PrimitiveTypes.Int32},
	{Name: "avg_temp", Type: arrow.PrimitiveTypes.Float64},
	{Name: "min_temp", Type: arrow.PrimitiveTypes.Float64},
	{Name: "max_temp", Type: arrow.PrimitiveTypes.Float64},
	{Name: "avg_humidity", Type: arrow.PrimitiveTypes.Float64},
	{Name: "avg_pressure", Type: arrow.PrimitiveTypes.Float64},
	{Name: "avg_wind_speed", Type: arrow.PrimitiveTypes.Float64},
	{Name: "shard_id", Type: arrow.BinaryTypes.String},
}, nil)

// RecordsToArrow конвертирует []AggregateRecord в Arrow RecordBatch.
func RecordsToArrow(records []AggregateRecord) (arrow.Record, error) {
	mem := memory.NewGoAllocator()
	b := array.NewRecordBuilder(mem, WeatherSchema)
	defer b.Release()

	cityB     := b.Field(0).(*array.StringBuilder)
	winStartB := b.Field(1).(*array.TimestampBuilder)
	winEndB   := b.Field(2).(*array.TimestampBuilder)
	countB    := b.Field(3).(*array.Int32Builder)
	avgTempB  := b.Field(4).(*array.Float64Builder)
	minTempB  := b.Field(5).(*array.Float64Builder)
	maxTempB  := b.Field(6).(*array.Float64Builder)
	avgHumB   := b.Field(7).(*array.Float64Builder)
	avgPresB  := b.Field(8).(*array.Float64Builder)
	avgWindB  := b.Field(9).(*array.Float64Builder)
	shardB    := b.Field(10).(*array.StringBuilder)

	for _, r := range records {
		cityB.Append(r.City)
		winStartB.Append(arrow.Timestamp(r.WindowStart.Unix()))
		winEndB.Append(arrow.Timestamp(r.WindowEnd.Unix()))
		countB.Append(r.Count)
		avgTempB.Append(r.AvgTemp)
		minTempB.Append(r.MinTemp)
		maxTempB.Append(r.MaxTemp)
		avgHumB.Append(r.AvgHumidity)
		avgPresB.Append(r.AvgPressure)
		avgWindB.Append(r.AvgWindSpeed)
		shardB.Append(r.ShardID)
	}

	return b.NewRecord(), nil
}

// FlightServer реализует Arrow Flight DoGet.
type FlightServer struct {
	flight.BaseFlightServer
	store *Store
}

func NewFlightServer(store *Store) *FlightServer {
	return &FlightServer{store: store}
}

// GetFlightInfo возвращает информацию о доступных потоках.
func (s *FlightServer) GetFlightInfo(
	ctx context.Context,
	req *flight.FlightDescriptor,
) (*flight.FlightInfo, error) {
	return &flight.FlightInfo{
		Schema:           flight.SerializeSchema(WeatherSchema, memory.NewGoAllocator()),
		FlightDescriptor: req,
		Endpoint: []*flight.FlightEndpoint{
			{Ticket: &flight.Ticket{Ticket: req.Cmd}},
		},
	}, nil
}

// DoGet отдаёт RecordBatch по тикету.
// Ticket = "all" → все записи, иначе → фильтр по городу.
func (s *FlightServer) DoGet(
	ticket *flight.Ticket,
	stream flight.FlightService_DoGetServer,
) error {
	query := string(ticket.Ticket)
	var records []AggregateRecord
	if query == "all" || query == "" {
		records = s.store.GetAll()
	} else {
		records = s.store.GetByCity(query)
	}

	if len(records) == 0 {
		records = []AggregateRecord{}
	}

	rec, err := RecordsToArrow(records)
	if err != nil {
		return fmt.Errorf("build arrow record: %w", err)
	}
	defer rec.Release()

	writer := flight.NewRecordWriter(stream, ipc.WithSchema(WeatherSchema))
	defer writer.Close()

	return writer.Write(rec)
}
