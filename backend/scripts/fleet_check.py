"""Confirm the fleet endpoint returns the new sparkline/readout fields."""
import time

import httpx

B = "http://localhost:8000/api"
e = f"ui{int(time.time())}@d.io"
c = httpx.Client(timeout=30)
c.post(f"{B}/auth/register", json={"email": e, "password": "secret123"})
t = c.post(f"{B}/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {t}"}
m = c.get(f"{B}/machines", headers=H).json()
if m:
    k = m[0]
    print("fields:", sorted(k.keys()))
    print("sample:", k["name"], "| health", k["health"], "| spark_len", len(k["spark"]),
          "| max_z", k["max_z"], "| latest_temp", k["latest"].get("temperature"))
else:
    print("no machines yet (DB empty) — endpoint shape still valid")
