# Ingestion gateway (Go)

High-concurrency front door for sensor telemetry. Accepts JSON batches, ACKs immediately
(202), forwards to the Python API (`/api/ingest/readings`) on worker goroutines with a
bounded queue + retry. Stdlib only — no external modules.

```bash
go build -o gateway
API_BASE=http://localhost:8000 API_TOKEN=<bearer> ./gateway
```

| Env | Default | Meaning |
|---|---|---|
| `GATEWAY_ADDR` | `:8080` | listen address |
| `API_BASE` | `http://localhost:8000` | Python API base URL |
| `API_TOKEN` | — | bearer token used to forward |
| `WORKERS` | `4` | forwarder goroutines |
| `QUEUE` | `1024` | max buffered batches (load-shed when full) |

Endpoints: `POST /ingest`, `GET /healthz`, `GET /stats`.

See [`../docs/phase9-edge.md`](../docs/phase9-edge.md).
