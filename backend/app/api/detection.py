"""Tunable detection: re-run with chosen algorithm/params and compare runs."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.anomaly.methods import METHODS
from app.db import get_db
from app.models import EtlRun, User
from app.schemas import DetectionRunOut, RerunRequest
from app.security import get_current_user
from app.services.detection import rerun_detection

router = APIRouter(prefix="/api/detect", tags=["detection"])


@router.get("/methods")
def list_methods(current: User = Depends(get_current_user)):
    return {"methods": METHODS}


@router.post("/rerun")
def rerun(
    payload: RerunRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if payload.method not in METHODS:
        raise HTTPException(status_code=400, detail=f"Unknown method: {payload.method}")
    if not (1 <= payload.window <= 60):
        raise HTTPException(status_code=400, detail="window must be 1-60")
    if not (1.0 <= payload.threshold <= 6.0):
        raise HTTPException(status_code=400, detail="threshold must be 1.0-6.0")
    result = rerun_detection(db, payload.method, payload.threshold, payload.window)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/runs", response_model=list[DetectionRunOut])
def list_runs(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(EtlRun).order_by(EtlRun.created_at.desc()).limit(25).all()
