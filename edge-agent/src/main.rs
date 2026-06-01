//! PdM Copilot — edge agent (Phase 9, path C).
//!
//! Runs on the factory floor (a cheap industrial PC / Raspberry Pi). It samples
//! sensors on an interval, and — crucially for India / Africa / SE Asia where the
//! internet is unreliable — it **buffers readings to local disk** and only deletes
//! them once the gateway has accepted them. A power cut or network outage never
//! loses data; the backlog flushes when connectivity returns.
//!
//! Sensor reads here are simulated; replace `sample_sensors()` with real Modbus /
//! OPC-UA / GPIO reads for a given installation.
//!
//! Build:  cargo build --release   (produces a small static-ish binary)
//! Env:
//!   GATEWAY_URL   gateway ingest URL   (default http://localhost:8080/ingest)
//!   MACHINE_ID    machine name to tag  (default EDGE-PUMP-001)
//!   INTERVAL_SECS sample interval      (default 5)
//!   BUFFER_FILE   offline spool path   (default ./edge_buffer.jsonl)

use serde::{Deserialize, Serialize};
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[derive(Serialize, Deserialize, Clone)]
struct Reading {
    machine: String,
    ts: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pressure: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    vibration: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    rpm: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    power_kw: Option<f64>,
}

#[derive(Serialize)]
struct Batch {
    readings: Vec<Reading>,
}

fn env(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_string())
}

fn now_iso() -> String {
    // Minimal RFC3339-ish UTC timestamp without pulling in a date crate.
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let days = secs / 86_400;
    let rem = secs % 86_400;
    let (h, m, s) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    // Civil date from days since epoch (Howard Hinnant's algorithm).
    let z = days as i64 + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let mth = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = if mth <= 2 { y + 1 } else { y };
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        year, mth, d, h, m, s
    )
}

/// Replace with real sensor reads (Modbus/OPC-UA/GPIO) for the installation.
fn sample_sensors(machine: &str) -> Reading {
    let t = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64();
    let wobble = (t / 7.0).sin();
    Reading {
        machine: machine.to_string(),
        ts: now_iso(),
        temperature: Some(62.0 + 4.0 * wobble),
        pressure: Some(101.0 + 2.0 * (t / 11.0).cos()),
        vibration: Some(1.2 + 0.3 * wobble.abs()),
        rpm: Some(1500.0),
        power_kw: Some(14.0 + 1.5 * wobble),
    }
}

fn append_to_buffer(path: &str, r: &Reading) {
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(f, "{}", serde_json::to_string(r).unwrap());
    }
}

fn read_buffer(path: &str) -> Vec<Reading> {
    let mut out = Vec::new();
    if let Ok(f) = File::open(path) {
        for line in BufReader::new(f).lines().map_while(Result::ok) {
            if let Ok(r) = serde_json::from_str::<Reading>(&line) {
                out.push(r);
            }
        }
    }
    out
}

/// POST the full backlog to the gateway. On success, clear the spool file.
fn try_flush(gateway: &str, token: Option<&str>, path: &str) {
    let pending = read_buffer(path);
    if pending.is_empty() {
        return;
    }
    let batch = Batch {
        readings: pending.clone(),
    };
    let mut req = ureq::post(gateway).set("Content-Type", "application/json");
    if let Some(t) = token {
        req = req.set("Authorization", &format!("Bearer {}", t));
    }
    match req.send_json(serde_json::to_value(&batch).unwrap()) {
        Ok(resp) if resp.status() >= 200 && resp.status() < 300 => {
            // Accepted — safe to clear the spool.
            let _ = File::create(path); // truncate
            println!("flushed {} buffered readings", batch.readings.len());
        }
        Ok(resp) => eprintln!("gateway returned {} — keeping buffer", resp.status()),
        Err(e) => eprintln!(
            "offline ({}). {} readings buffered locally",
            e,
            batch.readings.len()
        ),
    }
}

fn main() {
    let gateway = env("GATEWAY_URL", "http://localhost:8080/ingest");
    let machine = env("MACHINE_ID", "EDGE-PUMP-001");
    let interval = env("INTERVAL_SECS", "5").parse::<u64>().unwrap_or(5);
    let buffer = env("BUFFER_FILE", "./edge_buffer.jsonl");
    let token = std::env::var("API_TOKEN").ok();

    println!(
        "edge-agent: machine={} -> {} every {}s (buffer: {})",
        machine, gateway, interval, buffer
    );
    if !Path::new(&buffer).exists() {
        let _ = File::create(&buffer);
    }

    loop {
        let r = sample_sensors(&machine);
        append_to_buffer(&buffer, &r); // durable first — never lose a reading
        try_flush(&gateway, token.as_deref(), &buffer); // then attempt to sync
        thread::sleep(Duration::from_secs(interval));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn iso_timestamp_is_well_formed() {
        let ts = now_iso();
        // YYYY-MM-DDTHH:MM:SSZ  -> 20 chars, ends with Z
        assert_eq!(ts.len(), 20, "got {ts}");
        assert!(ts.ends_with('Z'));
        assert_eq!(&ts[4..5], "-");
        assert_eq!(&ts[10..11], "T");
    }

    #[test]
    fn reading_omits_absent_fields() {
        let r = Reading {
            machine: "M1".into(),
            ts: "2026-01-01T00:00:00Z".into(),
            temperature: Some(60.0),
            pressure: None,
            vibration: None,
            rpm: None,
            power_kw: None,
        };
        let json = serde_json::to_string(&r).unwrap();
        assert!(json.contains("\"temperature\":60.0"));
        assert!(
            !json.contains("pressure"),
            "None fields must be omitted: {json}"
        );
    }

    #[test]
    fn batch_roundtrips_through_json() {
        let b = Batch {
            readings: vec![Reading {
                machine: "PUMP-1".into(),
                ts: now_iso(),
                temperature: Some(63.0),
                pressure: None,
                vibration: None,
                rpm: Some(1500.0),
                power_kw: Some(14.0),
            }],
        };
        let v = serde_json::to_value(&b).unwrap();
        assert_eq!(v["readings"][0]["machine"], "PUMP-1");
        assert_eq!(v["readings"][0]["rpm"], 1500.0);
    }
}
