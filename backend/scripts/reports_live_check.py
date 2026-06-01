"""In-process check of the Phase 8 report flow."""
import time

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
e = f"rep{int(time.time())}@demo.io"
c.post("/api/auth/register", json={"email": e, "password": "secret123"})
tok = c.post("/api/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# ensure some energy data exists
c.post("/api/carbon/bills", headers=H, json={
    "kwh": 12000, "cost": 96000, "currency": "INR", "region": "IN",
    "period_start": "2026-04-01T00:00:00", "period_end": "2026-04-30T00:00:00"})

for fw, extra in [("ISSB", {}), ("CBAM", {"production_tonnes": 200}), ("BRSR", {})]:
    body = {"framework": fw, "region": "IN",
            "period_start": "2026-01-01T00:00:00", "period_end": "2026-12-31T00:00:00", **extra}
    r = c.post("/api/reports/generate", headers=H, json=body).json()
    rid = r["id"]
    html = c.get(f"/api/reports/{rid}/html", headers=H)
    print(f"{fw}: id={rid} total_tCO2e={r['payload']['summary']['total_tonnes_co2e']} "
          f"html={html.status_code} len={len(html.text)}")
print("frameworks:", [f["id"] for f in c.get("/api/reports/frameworks", headers=H).json()])
