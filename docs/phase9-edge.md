# Phase 9 — Edge agent, ingestion gateway, i18n, on-prem

This phase makes the platform work in real factory conditions: unreliable internet,
sensor-poor or sensor-rich sites at scale, local languages, and data-sovereignty needs.
It is **polyglot by necessity** — the Python core is unchanged; Go and Rust are satellites
around it (see [`product-vision.md`](product-vision.md) §5).

> Status: both services are **built, formatted, linted, unit-tested, and dockerized**, with
> CI jobs (Go: `gofmt`/`vet`/`test`/`build`; Rust: `fmt --check`/`clippy -D warnings`/`test`/
> `build`). The full **sensor → edge agent (offline buffer) → gateway → API** path has been
> verified end-to-end, including the offline-then-flush behaviour.
>
> Local note: the Rust edge agent is built with the GNU toolchain
> (`x86_64-pc-windows-gnu`) on Windows — its production target is Linux edge devices, which
> the `Dockerfile` builds. TLS is intentionally disabled (plain HTTP on the local hop;
> TLS terminates at the gateway/ingress), keeping the binary pure-Rust and tiny.

## Data flow

```
 [sensors] → Rust edge agent ──(offline buffer + sync)──▶ Go gateway ──▶ Python API
                edge-agent/                                gateway/      /api/ingest/readings
```

## Rust edge agent (`edge-agent/`)  — path C

Runs on the factory floor (cheap industrial PC / Raspberry Pi). Samples sensors on an
interval and **writes every reading to a local spool file first**, then attempts to sync to
the gateway. If the network or power drops, nothing is lost — the backlog flushes when
connectivity returns. Optimized for a tiny release binary.

```bash
cd edge-agent
cargo build --release          # or: docker build -t pdm-edge-agent .
GATEWAY_URL=http://<gateway-host>:8080/ingest MACHINE_ID=PUMP-001 ./target/release/pdm-edge-agent
```

Replace `sample_sensors()` in `src/main.rs` with real Modbus / OPC-UA / GPIO reads per
installation. Run `cargo fmt`, `cargo clippy -- -D warnings`, and `cargo test` before commit
(CI enforces these).

## Go ingestion gateway (`gateway/`) — path B at scale

A high-concurrency front door. Accepts JSON batches from many sites, acknowledges
immediately (HTTP 202), and forwards to the Python API on background workers with a bounded
queue + retry — so bursty telemetry never blocks the API. Stdlib only.

```bash
cd gateway
go build -o gateway
API_BASE=http://localhost:8000 API_TOKEN=<bearer> ./gateway   # listens on :8080
```

Endpoints: `POST /ingest`, `GET /healthz`, `GET /stats`.

## Python ingestion endpoint (already built, path B)

`POST /api/ingest/readings` accepts `{ "readings": [ {machine, ts, temperature, …, power_kw} ] }`,
upserts machines by name, and appends raw `SensorReading`s under a per-user `live-ingest`
dataset. Requires an operator+ token (auditors are read-only). This is the gateway's target
and can also be called directly for HTTP-capable sensors.

## i18n (`frontend/src/lib/i18n.js`)

A dependency-free dictionary + `t()` helper with a language switcher in the header
(English, Hindi, Bahasa Malaysia, Thai). Nav + key labels are wired as a demonstration;
remaining pages are translated incrementally by replacing literals with `t("…")` keys.

## On-prem / air-gapped

For data-sovereignty-conscious factories (India DPDP Act, etc.), the stack already runs
fully locally via `docker-compose.yml`. For an air-gapped install:

- Set `LLM_STUB_MODE=true` (no external LLM calls) **or** point `GROQ_API_KEY` at a
  self-hosted model gateway.
- The RAG embedding model (MiniLM ONNX) is downloaded once — pre-bake it into the image for
  air-gapped deployment.
- Keep Postgres, Redis, ChromaDB, and MLflow on the local network (already the default).
- The edge agent → gateway → API path runs entirely on-premise; nothing leaves the site.
