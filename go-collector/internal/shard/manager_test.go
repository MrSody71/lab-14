package shard

import (
	"testing"
)

func TestAssignCities_SingleShard(t *testing.T) {
	cities := []string{"A", "B", "C", "D", "E"}
	got := assignCities([]string{"shard-0"}, "shard-0", cities)
	if len(got) != 5 {
		t.Errorf("expected 5 cities, got %d: %v", len(got), got)
	}
}

func TestAssignCities_TwoShards(t *testing.T) {
	cities := []string{"A", "B", "C", "D"}
	shards := []string{"shard-0", "shard-1"}

	got0 := assignCities(shards, "shard-0", cities)
	want0 := []string{"A", "C"}
	if !equalSlices(got0, want0) {
		t.Errorf("shard-0: got %v, want %v", got0, want0)
	}

	got1 := assignCities(shards, "shard-1", cities)
	want1 := []string{"B", "D"}
	if !equalSlices(got1, want1) {
		t.Errorf("shard-1: got %v, want %v", got1, want1)
	}
}

func TestAssignCities_ThreeShards(t *testing.T) {
	cities := []string{"A", "B", "C", "D", "E", "F"}
	shards := []string{"s0", "s1", "s2"}

	got := assignCities(shards, "s1", cities)
	want := []string{"B", "E"}
	if !equalSlices(got, want) {
		t.Errorf("s1: got %v, want %v", got, want)
	}
}

func equalSlices(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
