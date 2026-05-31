import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Anomaly, Dataset, DatasetStatus, EtlRun, Machine, SensorReading, User
from app.schemas import DatasetOut
from app.security import get_current_user
from app.services.jobs import dispatch_dataset

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetOut)
def upload_csv(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    os.makedirs(settings.upload_dir, exist_ok=True)
    stored = os.path.join(settings.upload_dir, f"{uuid.uuid4().hex}_{file.filename}")
    with open(stored, "wb") as fh:
        fh.write(file.file.read())

    dataset = Dataset(
        user_id=current.id, filename=file.filename, status=DatasetStatus.PENDING
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    dispatch_dataset(background, dataset.id, stored)
    return dataset


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    # Single-tenant tool: all engineers share one fleet/data view.
    return db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(
    dataset_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    db.query(Anomaly).filter(Anomaly.dataset_id == dataset_id).delete(synchronize_session=False)
    db.query(SensorReading).filter(SensorReading.dataset_id == dataset_id).delete(synchronize_session=False)
    db.query(EtlRun).filter(EtlRun.dataset_id == dataset_id).delete(synchronize_session=False)
    db.delete(dataset)
    db.flush()

    # Prune machines that no longer have any readings.
    orphans = (
        db.query(Machine)
        .outerjoin(SensorReading, SensorReading.machine_id == Machine.id)
        .filter(SensorReading.id.is_(None))
        .all()
    )
    for m in orphans:
        db.query(Anomaly).filter(Anomaly.machine_id == m.id).delete(synchronize_session=False)
        db.delete(m)
    db.commit()
