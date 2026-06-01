"""Quick in-process end-to-end check of the Phase 6 carbon flow."""
import time

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
e = f"live{int(time.time())}@demo.io"
c.post("/api/auth/register", json={"email": e, "password": "secret123"})
tok = c.post("/api/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

print("bill:", c.post("/api/carbon/bills", headers=H, json={
    "kwh": 48000, "cost": 384000, "currency": "INR", "region": "IN",
    "period_start": "2026-05-01T00:00:00", "period_end": "2026-05-31T00:00:00"}).status_code)
print("fuel:", c.post("/api/carbon/fuel", headers=H, json={
    "fuel_type": "diesel", "runtime_hours": 90, "region": "IN",
    "period_start": "2026-05-01T00:00:00", "period_end": "2026-05-31T00:00:00"}).status_code)

s = c.get("/api/carbon/summary", headers=H).json()
print("total_tCO2e:", s["total_tonnes_co2e"], "| scope1:", s["scope1_kgco2e"],
      "| scope2:", s["scope2_kgco2e"], "| kwh:", s["total_kwh"])
print("by_source:", s["by_source"])
print("csv status:", c.get("/api/export/sustainability.csv", headers=H).status_code)
