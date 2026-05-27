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
