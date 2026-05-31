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
- **Phase 5** — GitHub Actions CI (pytest + lint), Docker Compose for the full stack,
  production Azure deployment + sample Power BI executive dashboard.
