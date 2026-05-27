package internal

import (
	"testing"
	"time"

	"github.com/apache/arrow/go/v17/arrow/array"
)

func makeAggRecord(city string) AggregateRecord {
	now := time.Now().UTC()
	return AggregateRecord{
		City:        city,
		WindowStart: now.Add(-60 * time.Second),
		WindowEnd:   now,
		Count:       3,
		AvgTemp:     15.0,
		MinTemp:     12.0,
		MaxTemp:     18.0,
		AvgHumidity: 65.0,
		AvgPressure: 1013.0,
		ShardID:     "shard-0",
	}
}

func TestRecordsToArrow_Empty(t *testing.T) {
	rec, err := RecordsToArrow([]AggregateRecord{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer rec.Release()

	if rec.NumRows() != 0 {
		t.Errorf("NumRows = %d, want 0", rec.NumRows())
	}
	if rec.Schema().NumFields() != 11 {
		t.Errorf("NumFields = %d, want 11", rec.Schema().NumFields())
	}
}

func TestRecordsToArrow_Data(t *testing.T) {
	records := []AggregateRecord{
		makeAggRecord("Moscow"),
		makeAggRecord("London"),
	}

	rec, err := RecordsToArrow(records)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer rec.Release()

	if rec.NumRows() != 2 {
		t.Fatalf("NumRows = %d, want 2", rec.NumRows())
	}

	cityCol, ok := rec.Column(0).(*array.String)
	if !ok {
		t.Fatal("column 0 is not *array.String")
	}
	if cityCol.Value(0) != "Moscow" {
		t.Errorf("row 0 city = %q, want Moscow", cityCol.Value(0))
	}
	if cityCol.Value(1) != "London" {
		t.Errorf("row 1 city = %q, want London", cityCol.Value(1))
	}
}
