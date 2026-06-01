"""In-process check of the Phase 9 ingestion endpoint (gateway target)."""
import time

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
e = f"ing{int(time.time())}@demo.io"
c.post("/api/auth/register", json={"email": e, "password": "secret123"})
tok = c.post("/api/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

batch = {"readings": [
    {"machine": "EDGE-PUMP-001", "ts": "2026-06-01T10:00:00Z", "temperature": 63.1, "power_kw": 14.2},
    {"machine": "EDGE-PUMP-001", "ts": "2026-06-01T10:00:05Z", "temperature": 64.0, "power_kw": 14.6},
    {"machine": "EDGE-MOTOR-002", "ts": "2026-06-01T10:00:05Z", "vibration": 2.1, "rpm": 1490},
]}
r = c.post("/api/ingest/readings", headers=H, json=batch).json()
print("ingest:", r)
fleet = c.get("/api/machines", headers=H).json()
print("machines now include:", [m["name"] for m in fleet if m["name"].startswith("EDGE-")])
