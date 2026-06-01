"""Seed sample energy/carbon data so the Carbon page shows real numbers.

Run AFTER reset_and_seed.py (which creates the fleet). Uses the running API.
"""
import time

import httpx

B = "http://localhost:8000/api"

e = f"carbon{int(time.time())}@demo.io"
c = httpx.Client(timeout=60)
c.post(f"{B}/auth/register", json={"email": e, "password": "secret123"})
t = c.post(f"{B}/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {t}"}

# 1. Rated power per machine (drives the energy-waste estimate).
RATED = {"PUMP-001": 15.0, "PUMP-002": 11.0, "MOTOR-001": 7.5, "VALVE-001": 2.2}
for m in c.get(f"{B}/machines", headers=H).json():
    kw = RATED.get(m["name"], 5.5)
    c.patch(f"{B}/carbon/machines/{m['id']}/rated-power", json={"rated_power_kw": kw}, headers=H)
    print(f"  rated {m['name']}: {kw} kW")

# 2. An electricity bill (Scope 2) — a month of grid power in India.
c.post(f"{B}/carbon/bills", headers=H, json={
    "kwh": 48000, "cost": 384000, "currency": "INR", "region": "IN",
    "period_start": "2026-05-01T00:00:00", "period_end": "2026-05-31T00:00:00",
})
print("  added electricity bill: 48,000 kWh")

# 3. A diesel genset fuel log (Scope 1) — runtime-based estimate.
c.post(f"{B}/carbon/fuel", headers=H, json={
    "fuel_type": "diesel", "runtime_hours": 90, "cost": 162000, "currency": "INR", "region": "IN",
    "period_start": "2026-05-01T00:00:00", "period_end": "2026-05-31T00:00:00",
})
print("  added diesel genset: 90 runtime hours")

s = c.post(f"{B}/carbon/recompute", headers=H).json()
print(f"\nInventory: {s['total_tonnes_co2e']} tCO2e "
      f"(Scope 1 {s['scope1_kgco2e']} / Scope 2 {s['scope2_kgco2e']} kg) | "
      f"avoidable {s['waste']['wasted_kgco2e']} kgCO2e")
print("Open the Carbon tab in the app.")
