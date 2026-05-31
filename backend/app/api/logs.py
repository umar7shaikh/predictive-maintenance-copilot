from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MaintenanceLog, User
from app.schemas import (
    MaintenanceLogCreate,
    MaintenanceLogOut,
    MaintenanceLogUpdate,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/logs", tags=["maintenance-log"])


@router.post("", response_model=MaintenanceLogOut)
def create_log(
    payload: MaintenanceLogCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    log = MaintenanceLog(
        recommendation_id=payload.recommendation_id,
        machine_id=payload.machine_id,
        notes=payload.notes,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[MaintenanceLogOut])
def list_logs(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(MaintenanceLog).order_by(MaintenanceLog.created_at.desc()).all()


@router.patch("/{log_id}", response_model=MaintenanceLogOut)
def update_log(
    log_id: int,
    payload: MaintenanceLogUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    log = db.get(MaintenanceLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    if payload.notes is not None:
        log.notes = payload.notes
    if payload.actioned is not None:
        log.actioned = payload.actioned
        log.actioned_at = datetime.utcnow() if payload.actioned else None
    db.commit()
    db.refresh(log)
    return log


@router.delete("/{log_id}", status_code=204)
def delete_log(
    log_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    log = db.get(MaintenanceLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    db.delete(log)
    db.commit()
