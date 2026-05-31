"""Verify delete endpoints work (uses a throwaway dataset; leaves seed data intact)."""
import os
import time

import httpx

B = "http://localhost:8000/api"
CSV = os.path.join(os.path.dirname(__file__), "..", "sample_data", "sample_sensors.csv")
e = f"del{int(time.time())}@demo.io"
c = httpx.Client(timeout=60)
c.post(f"{B}/auth/register", json={"email": e, "password": "secret123"})
t = c.post(f"{B}/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {t}"}

before = len(c.get(f"{B}/datasets", headers=H).json())
with open(CSV, "rb") as fh:
    ds = c.post(f"{B}/datasets/upload", files={"file": ("t.csv", fh, "text/csv")}, headers=H).json()
for _ in range(30):
    if c.get(f"{B}/datasets/{ds['id']}", headers=H).json()["status"] == "completed":
        break
    time.sleep(0.5)
mid = len(c.get(f"{B}/datasets", headers=H).json())

r = c.delete(f"{B}/datasets/{ds['id']}", headers=H)
after = len(c.get(f"{B}/datasets", headers=H).json())
gone = c.get(f"{B}/datasets/{ds['id']}", headers=H).status_code

print(f"datasets before={before} after_upload={mid} after_delete={after}")
print(f"DELETE status={r.status_code}  GET deleted dataset={gone} (expect 404)")
print("PASS" if r.status_code == 204 and gone == 404 and after == before else "FAIL")
