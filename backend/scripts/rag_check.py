"""Verify the live RAG path: upload manual PDF -> embed -> grounded, cited answer."""
import os
import time

import httpx

BASE = "http://localhost:8000/api"
PDF = os.path.join(os.path.dirname(__file__), "..", "sample_data", "sample_manual.pdf")
email = f"rag{int(time.time())}@demo.io"

with httpx.Client(timeout=180) as c:
    c.post(f"{BASE}/auth/register", json={"email": email, "password": "secret123"})
    tok = c.post(f"{BASE}/auth/login", data={"username": email, "password": "secret123"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    with open(PDF, "rb") as fh:
        doc = c.post(f"{BASE}/documents/upload", files={"file": ("sample_manual.pdf", fh, "application/pdf")}, headers=H).json()
    print("manual upload:", doc["status"], "(embedding model downloads on first run, please wait)")
    for _ in range(120):
        st = c.get(f"{BASE}/documents", headers=H).json()[0]
        if st["status"] in ("completed", "failed"):
            break
        time.sleep(1)
    print("manual:", st["status"], "chunks:", st["chunk_count"], "err:", st.get("error"))

    rec = c.post(
        f"{BASE}/recommend",
        headers=H,
        json={"question": "What does the manual say about vibration thresholds for the pump?"},
    ).json()
    print("\n=== GROUNDED ANSWER ===")
    print("VERDICT:", rec["verdict"])
    print("EXPLANATION:", rec["explanation"])
    for cit in rec.get("citations") or []:
        print(f"  CITATION [{cit.get('source')}, p.{cit.get('page')}]: {cit.get('snippet','')[:120]}")
