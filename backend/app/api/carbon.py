"""Energy & carbon endpoints (Phase 6).

Input paths: utility bills (grid electricity) and fuel logs (diesel gensets). The
service recomputes a traceable emission inventory and the predictive-maintenance
energy-waste estimate on demand.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    EmissionFactor,
    EnergySource,
    FuelLog,
    Machine,
    User,
    UtilityBill,
)
from app.schemas import (
    EmissionFactorOut,
    EnergySourceCreate,
    EnergySourceOut,
    FuelLogCreate,
    FuelLogOut,
    MachineRatedPowerUpdate,
    UtilityBillCreate,
    UtilityBillOut,
)
from app.security import get_current_user
from app.services import carbon

router = APIRouter(prefix="/api/carbon", tags=["carbon"])


# --- summary & recompute --------------------------------------------------

@router.get("/summary")
def summary(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    carbon.seed_factors_if_empty(db)
    return carbon.emissions_summary(db)


@router.post("/recompute")
def recompute(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    carbon.seed_factors_if_empty(db)
    result = carbon.recompute_emissions(db)
    return {**result, **carbon.emissions_summary(db)}


# --- emission factors (reference data) ------------------------------------

@router.get("/factors", response_model=list[EmissionFactorOut])
def list_factors(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    carbon.seed_factors_if_empty(db)
    return db.query(EmissionFactor).order_by(EmissionFactor.activity_type).all()


# --- energy sources -------------------------------------------------------

@router.post("/sources", response_model=EnergySourceOut)
def create_source(
    payload: EnergySourceCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    src = EnergySource(**payload.model_dump())
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


@router.get("/sources", response_model=list[EnergySourceOut])
def list_sources(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(EnergySource).order_by(EnergySource.created_at.desc()).all()


# --- utility bills (Scope 2 input) ----------------------------------------

@router.post("/bills", response_model=UtilityBillOut)
def create_bill(
    payload: UtilityBillCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if payload.period_end <= payload.period_start:
        raise HTTPException(status_code=422, detail="period_end must be after period_start")
    bill = UtilityBill(**payload.model_dump())
    db.add(bill)
    db.commit()
    db.refresh(bill)
    carbon.recompute_emissions(db)
    return bill


@router.get("/bills", response_model=list[UtilityBillOut])
def list_bills(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(UtilityBill).order_by(UtilityBill.period_start.desc()).all()


@router.delete("/bills/{bill_id}", status_code=204)
def delete_bill(
    bill_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    bill = db.get(UtilityBill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    db.delete(bill)
    db.commit()
    carbon.recompute_emissions(db)


# --- fuel logs (Scope 1 input) --------------------------------------------

@router.post("/fuel", response_model=FuelLogOut)
def create_fuel(
    payload: FuelLogCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if payload.period_end <= payload.period_start:
        raise HTTPException(status_code=422, detail="period_end must be after period_start")
    if payload.litres is None and payload.runtime_hours is None:
        raise HTTPException(status_code=422, detail="Provide litres or runtime_hours")
    log = FuelLog(**payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    carbon.recompute_emissions(db)
    return log


@router.get("/fuel", response_model=list[FuelLogOut])
def list_fuel(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(FuelLog).order_by(FuelLog.period_start.desc()).all()


@router.delete("/fuel/{log_id}", status_code=204)
def delete_fuel(
    log_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    log = db.get(FuelLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Fuel log not found")
    db.delete(log)
    db.commit()
    carbon.recompute_emissions(db)


# --- machine nameplate power (drives the waste estimate) ------------------

@router.patch("/machines/{machine_id}/rated-power")
def set_rated_power(
    machine_id: int,
    payload: MachineRatedPowerUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    machine.rated_power_kw = payload.rated_power_kw
    db.commit()
    return {"id": machine.id, "rated_power_kw": machine.rated_power_kw}
