package internal

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestGenerateForKnownCity(t *testing.T) {
	d, err := GenerateForCity("Moscow")
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if d.Temperature < 200 || d.Temperature > 350 {
		t.Errorf("Temperature out of range [200,350]: %f", d.Temperature)
	}
	if d.Humidity < 0 || d.Humidity > 100 {
		t.Errorf("Humidity out of range [0,100]: %d", d.Humidity)
	}
	if d.Pressure <= 900 {
		t.Errorf("Pressure should be > 900, got: %d", d.Pressure)
	}
}

func TestGenerateForUnknownCity(t *testing.T) {
	_, err := GenerateForCity("Atlantis")
	if err == nil {
		t.Fatal("expected error for unknown city, got nil")
	}
}

func TestBatchEndpoint(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/batch", BatchHandler)
	srv := httptest.NewServer(mux)
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/batch?cities=Moscow,London")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var results []owmResponse
	if err := json.NewDecoder(resp.Body).Decode(&results); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(results))
	}
}
