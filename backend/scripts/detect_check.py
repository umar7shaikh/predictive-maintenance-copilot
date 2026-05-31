"""Verify tunable detection (all algorithms), MLflow run logging, and forecasting."""
import time

import httpx

B = "http://localhost:8000/api"
e = f"det{int(time.time())}@d.io"
c = httpx.Client(timeout=120)
c.post(f"{B}/auth/register", json={"email": e, "password": "secret123"})
t = c.post(f"{B}/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {t}"}

print("methods:", c.get(f"{B}/detect/methods", headers=H).json()["methods"])

for method in ["zscore", "rolling_z", "ewma", "iqr", "isolation_forest"]:
    r = c.post(f"{B}/detect/rerun", headers=H, json={"method": method, "threshold": 3.0, "window": 10}).json()
    m = r["metrics"]
    print(f"  {method:16s} -> anomalies={m['anomalies_detected']:3d} flagged={m['machines_flagged']} high={m['high_severity']} run={r['mlflow_run_id'] is not None}")

runs = c.get(f"{B}/detect/runs", headers=H).json()
print("logged runs:", len(runs), "(side-by-side comparison available)")

fleet = c.get(f"{B}/machines", headers=H).json()
pump = next(m for m in fleet if m["name"] == "PUMP-001")
fc = c.get(f"{B}/machines/{pump['id']}/forecast", headers=H).json()
print("\nPUMP-001 forecast:")
for f in fc:
    eta = f"{f['eta_days']}d" if f["eta_days"] is not None else "—"
    print(f"  {f['parameter']:12s} current={f['current']} limit={f['limit']} {f['unit']:5s} slope/day={f['slope_per_day']} ETA={eta} [{f['status']}]")
