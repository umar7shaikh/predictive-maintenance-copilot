# Architecture

## Local (current)

```
┌────────────┐     ┌──────────────────────────── FastAPI backend ─────────────────────────┐
│  React/Vite │     │                                                                       │
│  (Recharts) │◀───▶│  /auth  /datasets  /machines  /recommend  /documents  /logs  /export  │
└────────────┘ HTTP │     │              │                  │              │                │
                    │     ▼              ▼                  ▼              ▼                │
                    │  Auth(JWT)   ETL (pandas)        RAG (Chroma)    MLflow (file store)  │
                    │              Anomaly (z-score)   Groq (Llama)                         │
                    └─────┬───────────────┬────────────────┬───────────────────────────────┘
                          ▼               ▼                ▼
                     PostgreSQL      ChromaDB (local)   mlruns/ (local)
```

Async work (CSV processing, PDF ingestion) runs in **FastAPI BackgroundTasks** today.

## Production mapping (Azure)

| Local component | Azure service |
|---|---|
| Raw CSV/PDF upload storage | **Azure Data Lake Storage (ADLS Gen2)** |
| pandas ETL + anomaly detection | **Azure Databricks** (PySpark) — swap `PandasETLEngine` → `SparkETLEngine` |
| MLflow file store | **Azure ML** model registry + experiment tracking |
| BackgroundTasks | **Azure Functions** (alert triggers) + queue |
| PostgreSQL | **Azure Database for PostgreSQL** |
| ChromaDB | **Azure AI Search** (vector) or managed Chroma |
| Redis/Celery (Phase 4) | **Azure Cache for Redis** + worker containers |
| FastAPI + React | **Azure Container Apps / App Service** |

The ETL engine is defined behind `app/etl/base.py:ETLEngine`, so the move from pandas to
Databricks PySpark is a single implementation swap with no caller changes.

## Roadmap

- **Phase 4 — done.** Celery + Redis async jobs (`USE_CELERY`), a `SparkETLEngine`
  selectable via `ETL_ENGINE=spark` (Java + winutils), and a local MLflow tracking
  server. All optional; pandas + BackgroundTasks remain the default.
- **Phase 5 — done.** GitHub Actions CI (backend pytest + frontend build on every push)
  and a Docker Compose stack (Postgres, Redis, API, Celery worker, MLflow server,
  frontend). Remaining: production Azure deployment + sample Power BI executive dashboard.
- **Phase 6 — done.** Energy & carbon core: Scope 1 (diesel gensets) + Scope 2
  (grid electricity) inventory from utility bills / fuel logs, versioned regional emission
  factors, and an energy-waste → CO₂ → cost estimate. `Carbon` page +
  `/api/export/sustainability.csv`. See [`esg.md`](esg.md).
- **Phase 7 — done.** Multi-tenant groundwork: `Organization` + `Site`, user roles
  (owner / manager / operator / read-only auditor), RBAC dependency, `Org` page. Additive —
  single-deployment installs keep working. Remaining hardening: row-level tenant isolation
  across all queries.
- **Phase 8 — done.** Regulatory report generator: one engine, three templates
  (ISSB/GHG, EU CBAM, India BRSR) over the audited carbon data, with methodology + factor
  provenance, downloadable printable reports. `Reports` page.
- **Phase 9 — done (Python verified; Go/Rust source shipped).** Go ingestion gateway +
  Rust offline-buffering edge agent + Python `/api/ingest/readings`; i18n scaffold
  (EN/HI/MS/TH) + on-prem notes. See [`phase9-edge.md`](phase9-edge.md).
- **Phase 10 — done.** Append-only, hash-chained audit ledger (tamper-evident) over report
  generation, with an integrity-verify endpoint and an Assurance panel — the trail BRSR Core
  / CBAM assurance need.
