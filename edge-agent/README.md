# Edge agent (Rust)

Runs on the factory floor. Samples sensors, **buffers every reading to local disk first**,
then syncs to the gateway — so unreliable internet or power cuts never lose data. Builds to
a small release binary for cheap industrial hardware.

```bash
cargo build --release
GATEWAY_URL=http://<gateway-host>:8080/ingest MACHINE_ID=PUMP-001 ./target/release/pdm-edge-agent
```

| Env | Default | Meaning |
|---|---|---|
| `GATEWAY_URL` | `http://localhost:8080/ingest` | gateway ingest URL |
| `MACHINE_ID` | `EDGE-PUMP-001` | machine name to tag readings |
| `INTERVAL_SECS` | `5` | sample interval |
| `BUFFER_FILE` | `./edge_buffer.jsonl` | offline spool path |
| `API_TOKEN` | — | optional bearer token |

Replace `sample_sensors()` in `src/main.rs` with real Modbus / OPC-UA / GPIO reads.

See [`../docs/phase9-edge.md`](../docs/phase9-edge.md).
