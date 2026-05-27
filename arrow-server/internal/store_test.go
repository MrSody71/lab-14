package internal

import (
	"testing"
	"time"
)

func makeRecord(city string) AggregateRecord {
	now := time.Now().UTC()
	return AggregateRecord{
		City:        city,
		WindowStart: now.Add(-60 * time.Second),
		WindowEnd:   now,
		Count:       5,
		AvgTemp:     15.0,
		ShardID:     "shard-0",
	}
}

func TestStore_AddAndGet(t *testing.T) {
	s := NewStore(100)
	s.Add(makeRecord("Moscow"))
	s.Add(makeRecord("Moscow"))
	s.Add(makeRecord("Moscow"))
	s.Add(makeRecord("London"))
	s.Add(makeRecord("London"))

	if got := len(s.GetAll()); got != 5 {
		t.Errorf("GetAll: got %d, want 5", got)
	}
	if got := len(s.GetByCity("Moscow")); got != 3 {
		t.Errorf("GetByCity(Moscow): got %d, want 3", got)
	}
	if got := len(s.GetByCity("Berlin")); got != 0 {
		t.Errorf("GetByCity(Berlin): got %d, want 0", got)
	}
}

func TestStore_MaxRecords(t *testing.T) {
	s := NewStore(3)
	for range 5 {
		s.Add(makeRecord("Tokyo"))
	}
	if got := len(s.GetAll()); got != 3 {
		t.Errorf("GetAll after overflow: got %d, want 3", got)
	}
}
