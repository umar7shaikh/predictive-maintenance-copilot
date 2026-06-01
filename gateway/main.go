// Ingestion gateway (Phase 9, path B at scale).
//
// A small, high-concurrency front door for sensor telemetry. It accepts JSON
// batches from many sites at once, acknowledges immediately (202), and forwards
// them to the Python API's /api/ingest/readings endpoint on background workers
// with a bounded queue and retry. This keeps the API responsive under bursty load.
//
// Stdlib only — no external modules. Build: `go build -o gateway` then run.
//
// Env:
//
//	GATEWAY_ADDR    listen address           (default :8080)
//	API_BASE        Python API base URL      (default http://localhost:8000)
//	API_TOKEN       bearer token for the API (required to forward)
//	WORKERS         forwarder goroutines     (default 4)
//	QUEUE           max buffered batches     (default 1024)
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync/atomic"
	"time"
)

type reading struct {
	Machine     string   `json:"machine"`
	TS          string   `json:"ts"`
	Temperature *float64 `json:"temperature,omitempty"`
	Pressure    *float64 `json:"pressure,omitempty"`
	Vibration   *float64 `json:"vibration,omitempty"`
	RPM         *float64 `json:"rpm,omitempty"`
	PowerKW     *float64 `json:"power_kw,omitempty"`
}

type batch struct {
	Readings []reading `json:"readings"`
}

var (
	apiBase   = env("API_BASE", "http://localhost:8000")
	apiToken  = os.Getenv("API_TOKEN")
	queue     chan batch
	accepted  int64
	forwarded int64
	dropped   int64
	failed    int64
)

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func envInt(k string, def int) int {
	if v := os.Getenv(k); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func main() {
	queue = make(chan batch, envInt("QUEUE", 1024))
	workers := envInt("WORKERS", 4)
	for i := 0; i < workers; i++ {
		go forwarder(i)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/ingest", handleIngest)
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Write([]byte("ok"))
	})
	mux.HandleFunc("/stats", func(w http.ResponseWriter, _ *http.Request) {
		json.NewEncoder(w).Encode(map[string]int64{
			"accepted":  atomic.LoadInt64(&accepted),
			"forwarded": atomic.LoadInt64(&forwarded),
			"dropped":   atomic.LoadInt64(&dropped),
			"failed":    atomic.LoadInt64(&failed),
			"queued":    int64(len(queue)),
		})
	})

	addr := env("GATEWAY_ADDR", ":8080")
	log.Printf("ingestion gateway listening on %s -> %s (%d workers)", addr, apiBase, workers)
	srv := &http.Server{Addr: addr, Handler: mux, ReadTimeout: 15 * time.Second}
	log.Fatal(srv.ListenAndServe())
}

// handleIngest validates the batch and enqueues it without blocking the caller.
func handleIngest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var b batch
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil || len(b.Readings) == 0 {
		http.Error(w, "invalid or empty batch", http.StatusBadRequest)
		return
	}
	atomic.AddInt64(&accepted, int64(len(b.Readings)))
	select {
	case queue <- b: // buffered; a worker will forward it
		w.WriteHeader(http.StatusAccepted)
		w.Write([]byte(`{"status":"accepted"}`))
	default: // queue full -> shed load rather than block live sensors
		atomic.AddInt64(&dropped, int64(len(b.Readings)))
		http.Error(w, "queue full", http.StatusServiceUnavailable)
	}
}

// forwarder drains the queue and POSTs batches to the Python API with simple retry.
func forwarder(id int) {
	client := &http.Client{Timeout: 20 * time.Second}
	for b := range queue {
		body, _ := json.Marshal(b)
		var ok bool
		for attempt := 0; attempt < 3 && !ok; attempt++ {
			if attempt > 0 {
				time.Sleep(time.Duration(attempt) * 500 * time.Millisecond)
			}
			ok = post(client, body)
		}
		if ok {
			atomic.AddInt64(&forwarded, int64(len(b.Readings)))
		} else {
			atomic.AddInt64(&failed, int64(len(b.Readings)))
			log.Printf("worker %d: batch of %d failed after retries", id, len(b.Readings))
		}
	}
}

func post(client *http.Client, body []byte) bool {
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		apiBase+"/api/ingest/readings", bytes.NewReader(body))
	if err != nil {
		return false
	}
	req.Header.Set("Content-Type", "application/json")
	if apiToken != "" {
		req.Header.Set("Authorization", "Bearer "+apiToken)
	}
	resp, err := client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode >= 200 && resp.StatusCode < 300
}
