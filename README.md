# Predictive Maintenance Copilot

An AI-powered predictive maintenance platform for industrial equipment (hydraulic
pumps, motors, valves, fluid conveyance). Engineers upload sensor data and equipment
manuals; the system detects anomalies, reasons over them with an LLM grounded in the
manuals, and delivers structured maintenance recommendations in plain English.

> Built and runs **natively on Windows** (no Docker/WSL required). The architecture
> maps cleanly onto Azure for production — see [`docs/architecture.md`](docs/architecture.md).

## Features

1. **Sensor data analysis** — upload a CSV of time-series readings (temperature,
   pressure, vibration, RPM) across machines. Statistical z-score anomaly detection per
   machine/parameter, severity scoring (HIGH / MEDIUM / MONITOR), trend detection, and
   time-series charts with anomalies highlighted.
2. **Maintenance manual intelligence (RAG)** — upload PDF manuals; they're chunked,
   embedded (MiniLM via ONNX) into ChromaDB, and retrieved to ground AI answers.
3. **AI recommendation engine** — combines the anomaly summary + retrieved manual
   context + your question into a structured verdict (URGENT SERVICE / SCHEDULE SERVICE
   / MONITOR / SAFE) with explanation and citations. Follow-up chat with memory.
4. **ETL pipeline** — Extract → Transform (null handling, unit normalization, rolling
   averages, rate-of-change) → Load to PostgreSQL. Behind a swappable engine interface.
5. **MLflow tracking** — every detection run logs params (z-threshold, window) and
   metrics (anomalies, machines flagged) for an auditable MLOps layer.
6. **Fleet dashboard** — all machines color-coded by health, sorted by severity, with
   drilldown into per-machine charts and anomaly tables.
7. **Maintenance log** — every recommendation is saved with a timestamp and can be
   marked actioned with notes (compliance / warranty audit trail).
8. **Power BI export** — clean CSVs formatted for Power BI ingestion; data model in
   [`docs/powerbi.md`](docs/powerbi.md).

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI, JWT auth (passlib + python-jose) |
| DB | PostgreSQL (SQLAlchemy + Alembic) |
| ETL / detection | pandas, numpy, scipy (PySpark-swappable interface) |
| MLOps | MLflow (local file store) |
| RAG | ChromaDB + all-MiniLM-L6-v2 (ONNX) |
| LLM | Groq (Llama 3.1) with a deterministic stub fallback |
| Frontend | React + Vite + Tailwind + Recharts |
| Async (later) | FastAPI BackgroundTasks now; Celery + Redis/Memurai in Phase 4 |

## Prerequisites (Windows)

- Python 3.11 (`py -3.11`)
- Node 20+
- PostgreSQL (this project was set up against PostgreSQL 18 on **port 5433**)

## Setup

### 1. Database
Create the database (using the bundled psql, adjust path/port if needed):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -U postgres -p 5433 pdm_copilot
```

### 2. Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env   # then edit DATABASE_URL password + GROQ_API_KEY
.\.venv\Scripts\python.exe scripts\gen_sample_data.py   # sample CSV + manual
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

App at http://localhost:5173

### 4. MLflow UI (optional)

```powershell
cd backend
.\.venv\Scripts\mlflow.exe ui --backend-store-uri ./mlruns
```

## Demo flow

1. Register an account → sign in.
2. **Upload Data** → upload `backend/sample_data/sample_sensors.csv` and
   `sample_data/sample_manual.pdf`.
3. **Fleet** → PUMP-001 shows critical (overheating + vibration trend).
4. Click PUMP-001 → see charts with anomalies highlighted.
5. **AI Copilot** → ask "Is PUMP-001 safe to keep running?" → get a cited verdict.
6. Save it → **Maintenance Log** → mark actioned with a note.
7. Export Power BI CSVs from `/api/export/sensors.csv` and `/api/export/anomalies.csv`.

## Configuration notes

- **No Groq key?** Set `LLM_STUB_MODE=true` (or leave `GROQ_API_KEY` blank) — the app
  returns deterministic severity-based verdicts so the demo still works.
- **RAG model download** — first PDF upload downloads the MiniLM ONNX model (~80MB).
- Roadmap (phases 4–5: Celery/Redis, PySpark engine, Docker, CI) in
  [`docs/architecture.md`](docs/architecture.md).
