"""Hit the running server (http://localhost:8000) to verify the live stack:
Postgres + real Groq. Run: .\.venv\Scripts\python.exe scripts\live_check.py
"""
import os
import time

import httpx

BASE = "http://localhost:8000/api"
CSV = os.path.join(os.path.dirname(__file__), "..", "sample_data", "sample_sensors.csv")
email = f"live{int(time.time())}@demo.io"

with httpx.Client(timeout=60) as c:
    c.post(f"{BASE}/auth/register", json={"email": email, "password": "secret123"})
    tok = c.post(f"{BASE}/auth/login", data={"username": email, "password": "secret123"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    print("login OK against Postgres")

    with open(CSV, "rb") as fh:
        ds = c.post(f"{BASE}/datasets/upload", files={"file": ("sample_sensors.csv", fh, "text/csv")}, headers=H).json()
    for _ in range(20):
        st = c.get(f"{BASE}/datasets/{ds['id']}", headers=H).json()
        if st["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)
    print("dataset:", st["status"], "rows:", st["row_count"])

    fleet = c.get(f"{BASE}/machines", headers=H).json()
    for m in fleet:
        print(f"  {m['name']}: {m['health']} (high={m['high_count']} med={m['medium_count']} mon={m['monitor_count']})")
    pump = next(m for m in fleet if m["name"] == "PUMP-001")

    rec = c.post(
        f"{BASE}/recommend",
        headers=H,
        json={"machine_id": pump["id"], "question": "Is PUMP-001 safe to keep running? What does the manual advise?"},
    ).json()
    print("\n=== REAL GROQ RECOMMENDATION ===")
    print("VERDICT:", rec["verdict"])
    print("EXPLANATION:", rec["explanation"])
    print("CITATIONS:", len(rec.get("citations") or []))
