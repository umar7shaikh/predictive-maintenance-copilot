"""In-process check of Phase 7 org/role wiring."""
import time

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
e = f"org{int(time.time())}@demo.io"
c.post("/api/auth/register", json={"email": e, "password": "secret123"})
tok = c.post("/api/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

me = c.get("/api/auth/me", headers=H).json()
print("me:", {"email": me["email"], "role": me["role"], "org_id": me["org_id"]})

org = c.get("/api/org", headers=H).json()
print("org:", org.get("name"), "country:", org.get("country"))

# operator should be blocked from creating a site (manager+)
site = c.post("/api/org/sites", headers=H, json={"name": "Plant A", "region": "IN"})
print("operator create site ->", site.status_code, "(expect 403)")

# operator may still generate a report (auditors couldn't)
rep = c.post("/api/reports/generate", headers=H, json={
    "framework": "ISSB", "region": "IN",
    "period_start": "2026-01-01T00:00:00", "period_end": "2026-12-31T00:00:00"})
print("operator generate report ->", rep.status_code, "(expect 200)")
