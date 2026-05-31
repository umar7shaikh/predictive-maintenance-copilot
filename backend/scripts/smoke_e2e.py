"""End-to-end backend smoke test against a throwaway SQLite DB (no secrets needed).

Sets env BEFORE importing the app so the engine/config pick up the test settings.
Run from backend/:  .\.venv\Scripts\python.exe scripts\smoke_e2e.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

DB_PATH = os.path.join(BACKEND, "smoke.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["LLM_STUB_MODE"] = "true"
os.environ["MLFLOW_TRACKING_URI"] = f"file:{os.path.join(BACKEND, 'mlruns')}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import engine  # noqa: E402
from sqlalchemy import event  # noqa: E402

# SQLite + threads safety for the test client background tasks.
if engine.url.get_backend_name() == "sqlite":
    @event.listens_for(engine, "connect")
    def _fk(dbapi_con, _):
        pass

from app.main import app  # noqa: E402
from app.db import Base  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)
CSV = os.path.join(BACKEND, "sample_data", "sample_sensors.csv")
assert os.path.exists(CSV), "Run gen_sample_data.py first"

ok = 0


def check(label, cond):
    global ok
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}")
    if cond:
        ok += 1
    else:
        raise SystemExit(f"Smoke test failed at: {label}")


# 1. Register + login
r = client.post("/api/auth/register", json={"email": "eng@demo.io", "password": "secret123"})
check("register", r.status_code in (201, 400))
r = client.post("/api/auth/login", data={"username": "eng@demo.io", "password": "secret123"})
check("login returns token", r.status_code == 200 and "access_token" in r.json())
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

# 2. Upload CSV (background task runs synchronously within TestClient)
with open(CSV, "rb") as fh:
    r = client.post("/api/datasets/upload", files={"file": ("sample_sensors.csv", fh, "text/csv")}, headers=H)
check("csv upload accepted", r.status_code == 200)
ds = r.json()
r = client.get(f"/api/datasets/{ds['id']}", headers=H)
check("dataset completed", r.json()["status"] == "completed")
print("      rows processed:", r.json()["row_count"])

# 3. Fleet
r = client.get("/api/machines", headers=H)
machines = r.json()
check("fleet has 4 machines", len(machines) == 4)
pump = next(m for m in machines if m["name"] == "PUMP-001")
check("PUMP-001 flagged critical (red)", pump["health"] == "red")
print("      PUMP-001 anomalies:", pump["anomaly_count"], "high:", pump["high_count"])

# 4. Machine detail
r = client.get(f"/api/machines/{pump['id']}", headers=H)
detail = r.json()
check("machine detail has readings", len(detail["readings"]) > 0)
check("machine detail has anomalies", len(detail["anomalies"]) > 0)

# 5. Recommendation (stub)
r = client.post("/api/recommend", json={"machine_id": pump["id"], "question": "Is PUMP-001 safe to run?"}, headers=H)
rec = r.json()
check("recommendation returns a verdict", rec["verdict"] in {"URGENT_SERVICE", "SCHEDULE_SERVICE", "MONITOR", "SAFE"})
print("      verdict:", rec["verdict"])

# 6. Save to maintenance log + action it
r = client.post("/api/logs", json={"recommendation_id": rec["id"], "machine_id": pump["id"]}, headers=H)
log = r.json()
check("log created", r.status_code == 200)
r = client.patch(f"/api/logs/{log['id']}", json={"actioned": True, "notes": "Inspected bearing"}, headers=H)
check("log marked actioned", r.json()["actioned"] is True)

# 7. Power BI export
r = client.get("/api/export/sensors.csv", headers=H)
check("sensors export csv", r.status_code == 200 and "machine,timestamp" in r.text)
r = client.get("/api/export/anomalies.csv", headers=H)
check("anomalies export csv", r.status_code == 200 and "severity" in r.text)

print(f"\nAll {ok} checks passed.")
engine.dispose()
try:
    os.remove(DB_PATH)
except OSError:
    pass  # Windows may still hold the sqlite file handle briefly
