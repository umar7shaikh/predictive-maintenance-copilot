"""Verify section-aware chunking + relevance scores flow into citations.
Assumes data already seeded (manual embedded). Just asks and inspects citations."""
import time

import httpx

B = "http://localhost:8000/api"
e = f"sec{int(time.time())}@d.io"
c = httpx.Client(timeout=60)
c.post(f"{B}/auth/register", json={"email": e, "password": "secret123"})
t = c.post(f"{B}/auth/login", data={"username": e, "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {t}"}

fleet = c.get(f"{B}/machines", headers=H).json()
pump = next((m for m in fleet if m["name"] == "PUMP-001"), None)
rec = c.post(
    f"{B}/recommend",
    headers=H,
    json={"machine_id": pump["id"] if pump else None,
          "question": "What are the vibration thresholds for the pump?"},
).json()
print("VERDICT:", rec["verdict"])
print("citations:")
for cit in rec.get("citations") or []:
    print(f"  source={cit.get('source')} | section={cit.get('section')!r} | "
          f"page={cit.get('page')} | rel={cit.get('score')}")
    print(f"     {cit.get('snippet','')[:90]}")
