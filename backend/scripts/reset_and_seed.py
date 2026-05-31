"""Reset all domain data and seed exactly one clean sensor dataset + manual."""
import os
import time

import httpx

B = "http://localhost:8000/api"
HERE = os.path.dirname(__file__)
CSV = os.path.join(HERE, "..", "sample_data", "sample_sensors.csv")
PDF = os.path.join(HERE, "..", "sample_data", "sample_manual.pdf")

e = f"seed{int(time.time())}@demo.io"
c = httpx.Client(timeout=180)
c.post(f"{B}/auth/register", json={"email": e, "password": "secret123"})
t = c.post(f"{B}/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {t}"}

print("reset:", c.post(f"{B}/admin/reset", headers=H).json())

with open(CSV, "rb") as fh:
    ds = c.post(f"{B}/datasets/upload", files={"file": ("sample_sensors.csv", fh, "text/csv")}, headers=H).json()
for _ in range(30):
    st = c.get(f"{B}/datasets/{ds['id']}", headers=H).json()
    if st["status"] in ("completed", "failed"):
        break
    time.sleep(0.5)
print("dataset:", st["status"], "rows:", st["row_count"])

with open(PDF, "rb") as fh:
    c.post(f"{B}/documents/upload", files={"file": ("sample_manual.pdf", fh, "application/pdf")}, headers=H)
for _ in range(120):
    docs = c.get(f"{B}/documents", headers=H).json()
    if docs and docs[0]["status"] in ("completed", "failed"):
        break
    time.sleep(1)
print("manual:", docs[0]["status"], "chunks:", docs[0]["chunk_count"])

fleet = c.get(f"{B}/machines", headers=H).json()
for m in fleet:
    print(f"  {m['name']}: {m['health']} anomalies={m['anomaly_count']} z={m['max_z']}")
print("\nClean data seeded. Refresh the app.")
