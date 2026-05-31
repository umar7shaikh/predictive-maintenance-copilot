"""Generate synthetic sensor data + a sample equipment manual for the demo.

Usage (from backend/):
    py -3.11 scripts/gen_sample_data.py

Outputs:
    sample_data/sample_sensors.csv   multi-machine time series with injected anomalies
    sample_data/sample_manual.pdf    short maintenance manual for RAG
"""
import csv
import math
import os
import random
from datetime import datetime, timedelta

random.seed(42)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")

# (name, type, baselines: temp C, pressure bar, vibration mm/s, rpm)
MACHINES = [
    ("PUMP-001", {"temperature": 62, "pressure": 145, "vibration": 2.1, "rpm": 1480}),
    ("PUMP-002", {"temperature": 58, "pressure": 150, "vibration": 1.8, "rpm": 1500}),
    ("MOTOR-001", {"temperature": 70, "pressure": 0, "vibration": 1.5, "rpm": 2950}),
    ("VALVE-001", {"temperature": 45, "pressure": 90, "vibration": 0.6, "rpm": 0}),
]

POINTS = 240            # hourly readings -> 10 days
NOISE = {"temperature": 1.2, "pressure": 2.5, "vibration": 0.15, "rpm": 8}


def generate_csv(path: str) -> None:
    start = datetime(2026, 5, 1, 0, 0, 0)
    rows = []
    for name, base in MACHINES:
        # PUMP-001 develops a worsening overheating + vibration trend (HIGH).
        # PUMP-002 gets isolated pressure spikes (MONITOR/MEDIUM).
        for i in range(POINTS):
            ts = start + timedelta(hours=i)
            reading = {}
            for param, b in base.items():
                if b == 0:
                    reading[param] = 0.0
                    continue
                drift = 0.0
                if name == "PUMP-001" and param in ("temperature", "vibration"):
                    drift = (i / POINTS) * (b * 0.25)  # gradual degradation
                val = b + drift + random.gauss(0, NOISE[param])
                reading[param] = round(val, 2)

            # Inject sharp anomalies.
            if name == "PUMP-001" and i in (210, 225, 238):
                reading["temperature"] = round(base["temperature"] * 1.6, 2)
                reading["vibration"] = round(base["vibration"] * 2.4, 2)
            if name == "PUMP-002" and i in (120, 150):
                reading["pressure"] = round(base["pressure"] * 1.5, 2)

            rows.append(
                [ts.isoformat(), name, reading["temperature"], reading["pressure"],
                 reading["vibration"], reading["rpm"]]
            )

    # Sprinkle a few missing values to exercise null handling.
    for r in random.sample(rows, k=8):
        r[random.randint(2, 5)] = ""

    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "machine_id", "temperature", "pressure", "vibration", "rpm"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {path}")


MANUAL_SECTIONS = [
    ("1. Hydraulic Pump Operating Limits",
     "Normal operating temperature for the HP-series hydraulic pump is 55-68 C. "
     "Sustained operation above 75 C indicates degraded cooling or internal leakage and "
     "requires URGENT service. Normal discharge pressure is 140-155 bar."),
    ("2. Vibration Thresholds",
     "Baseline vibration for the HP-series pump is 1.5-2.5 mm/s RMS. Readings between "
     "2.5 and 4.0 mm/s indicate early bearing wear; schedule inspection. Readings above "
     "4.0 mm/s indicate imminent bearing failure and require immediate shutdown."),
    ("3. Pressure Spikes",
     "Transient pressure spikes above 165 bar suggest a sticking relief valve or "
     "blocked return line. Investigate the relief valve and filter if spikes recur."),
    ("4. Motor Maintenance",
     "Electric motors should run below 80 C. Lubricate bearings every 4000 operating "
     "hours. A rising temperature trend combined with vibration is a leading indicator "
     "of bearing failure."),
    ("5. Preventive Maintenance Schedule",
     "Inspect seals and filters every 500 hours. Replace hydraulic fluid every 2000 "
     "hours. Verify alignment and mounting bolts monthly."),
]


def generate_pdf(path: str) -> None:
    try:
        from fpdf import FPDF
    except ImportError:
        print("fpdf2 not installed; skipping PDF. Run: pip install fpdf2")
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "HP-Series Equipment Maintenance Manual", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for title, body in MANUAL_SECTIONS:
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, body, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    pdf.output(path)
    print(f"Wrote manual -> {path}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    generate_csv(os.path.join(OUT_DIR, "sample_sensors.csv"))
    generate_pdf(os.path.join(OUT_DIR, "sample_manual.pdf"))
