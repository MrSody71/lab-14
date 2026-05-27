package shard

import "sort"

// assignCities distributes cities across shards using round-robin by sorted shard ID.
// Returns the slice of cities assigned to myID. If myID is not in shardIDs or
// shardIDs is empty, all cities are returned.
func assignCities(shardIDs []string, myID string, cities []string) []string {
	if len(shardIDs) == 0 {
		return cities
	}

	sorted := make([]string, len(shardIDs))
	copy(sorted, shardIDs)
	sort.Strings(sorted)

	myPos := -1
	for i, id := range sorted {
		if id == myID {
			myPos = i
			break
		}
	}
	if myPos == -1 {
		return cities
	}

	result := make([]string, 0)
	for i, city := range cities {
		if i%len(sorted) == myPos {
			result = append(result, city)
		}
	}
	return result
}
