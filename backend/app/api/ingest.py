"""Live sensor ingestion (Phase 9, path B).

A JSON batch endpoint that the Go ingestion gateway (and the Rust edge agent, when
online) forwards normalized readings to. Upserts machines by name and appends raw
SensorReadings under a per-user 'live-ingest' dataset. ETL/detection run separately.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Dataset, DatasetStatus, Machine, Role, SensorReading, User
from app.schemas import IngestBatch
from app.security import require_role

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


def _live_dataset(db: Session, user_id: int) -> Dataset:
    ds = (
        db.query(Dataset)
        .filter(Dataset.user_id == user_id, Dataset.filename == "live-ingest")
        .first()
    )
    if not ds:
        ds = Dataset(user_id=user_id, filename="live-ingest", status=DatasetStatus.COMPLETED)
        db.add(ds)
        db.flush()
    return ds


@router.post("/readings")
def ingest_readings(
    batch: IngestBatch,
    db: Session = Depends(get_db),
    current: User = Depends(require_role(Role.OPERATOR)),  # auditors are read-only
):
    if not batch.readings:
        return {"ingested": 0, "machines": 0}

    ds = _live_dataset(db, current.id)
    machine_ids: dict[str, int] = {m.name: m.id for m in db.query(Machine).all()}
    new_machines = 0

    for r in batch.readings:
        mid = machine_ids.get(r.machine)
        if mid is None:
            m = Machine(name=r.machine, machine_type="sensor")
            db.add(m)
            db.flush()
            mid = m.id
            machine_ids[r.machine] = mid
            new_machines += 1
        db.add(SensorReading(
            machine_id=mid, dataset_id=ds.id, ts=r.ts,
            temperature=r.temperature, pressure=r.pressure,
            vibration=r.vibration, rpm=r.rpm, power_kw=r.power_kw,
        ))

    ds.row_count = (ds.row_count or 0) + len(batch.readings)
    db.commit()
    return {"ingested": len(batch.readings), "new_machines": new_machines, "dataset_id": ds.id}
