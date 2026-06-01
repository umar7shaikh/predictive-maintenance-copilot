package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHandleIngestAcceptsValidBatch(t *testing.T) {
	queue = make(chan batch, 4)
	body, _ := json.Marshal(batch{Readings: []reading{{Machine: "M1", TS: "2026-01-01T00:00:00Z"}}})
	req := httptest.NewRequest(http.MethodPost, "/ingest", bytes.NewReader(body))
	w := httptest.NewRecorder()

	handleIngest(w, req)

	if w.Code != http.StatusAccepted {
		t.Fatalf("expected 202, got %d", w.Code)
	}
	if len(queue) != 1 {
		t.Fatalf("expected 1 queued batch, got %d", len(queue))
	}
}

func TestHandleIngestRejectsEmptyBatch(t *testing.T) {
	queue = make(chan batch, 4)
	body, _ := json.Marshal(batch{Readings: []reading{}})
	req := httptest.NewRequest(http.MethodPost, "/ingest", bytes.NewReader(body))
	w := httptest.NewRecorder()

	handleIngest(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for empty batch, got %d", w.Code)
	}
}

func TestHandleIngestRejectsGet(t *testing.T) {
	queue = make(chan batch, 4)
	req := httptest.NewRequest(http.MethodGet, "/ingest", nil)
	w := httptest.NewRecorder()

	handleIngest(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405 for GET, got %d", w.Code)
	}
}

func TestQueueFullShedsLoad(t *testing.T) {
	queue = make(chan batch, 1)
	queue <- batch{Readings: []reading{{Machine: "X"}}} // fill it
	body, _ := json.Marshal(batch{Readings: []reading{{Machine: "M1"}}})
	req := httptest.NewRequest(http.MethodPost, "/ingest", bytes.NewReader(body))
	w := httptest.NewRecorder()

	handleIngest(w, req)

	if w.Code != http.StatusServiceUnavailable {
		t.Fatalf("expected 503 when queue full, got %d", w.Code)
	}
}
