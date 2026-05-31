from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Anomaly, Machine, SensorReading, User
from app.schemas import AnomalyOut, MachineDetail, MachineHealth, ReadingPoint
from app.security import get_current_user
from app.services.fleet import machine_health

router = APIRouter(prefix="/api/machines", tags=["machines"])

_SEVERITY_RANK = {"red": 0, "yellow": 1, "green": 2}


@router.get("", response_model=list[MachineHealth])
def fleet(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    machines = db.query(Machine).all()
    health = [machine_health(db, m) for m in machines]
    # Sort by severity (red first), then by anomaly count desc.
    health.sort(key=lambda h: (_SEVERITY_RANK[h["health"]], -h["anomaly_count"]))
    return health


@router.get("/{machine_id}", response_model=MachineDetail)
def machine_detail(
    machine_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    readings = (
        db.query(SensorReading)
        .filter(SensorReading.machine_id == machine_id)
        .order_by(SensorReading.ts.asc())
        .all()
    )
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.machine_id == machine_id)
        .order_by(Anomaly.ts.asc())
        .all()
    )
    return MachineDetail(
        machine=MachineHealth(**machine_health(db, machine)),
        readings=[ReadingPoint.model_validate(r, from_attributes=True) for r in readings],
        anomalies=[AnomalyOut.model_validate(a, from_attributes=True) for a in anomalies],
    )


@router.delete("/{machine_id}", status_code=204)
def delete_machine(
    machine_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    db.query(Anomaly).filter(Anomaly.machine_id == machine_id).delete(synchronize_session=False)
    db.query(SensorReading).filter(SensorReading.machine_id == machine_id).delete(synchronize_session=False)
    db.delete(machine)
    db.commit()
