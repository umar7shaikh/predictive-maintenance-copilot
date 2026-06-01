"""FastAPI application entrypoint."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.api import (
    admin,
    audit,
    auth,
    carbon,
    chat,
    datasets,
    detection,
    documents,
    export,
    ingest,
    logs,
    machines,
    org,
    recommendations,
    reports,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Predictive Maintenance Copilot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    os.makedirs(settings.upload_dir, exist_ok=True)
    # Dev convenience: ensure tables exist. Alembic remains the source of truth.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


for module in (
    auth, datasets, machines, recommendations, documents, chat, logs, export, admin,
    detection, carbon, reports, org, audit, ingest,
):
    app.include_router(module.router)
