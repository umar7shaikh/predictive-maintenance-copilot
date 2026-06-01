"""Power BI export endpoints: clean, flat CSVs with documented columns."""
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Anomaly, EmissionRecord, Machine, SensorReading, User
from app.security import get_current_user
from app.services import carbon

router = APIRouter(prefix="/api/export", tags=["export"])


def _csv_response(header: list[str], rows, filename: str) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/sensors.csv")
def export_sensors(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    name_by_id = {m.id: m.name for m in db.query(Machine).all()}
    header = [
        "machine", "timestamp", "temperature", "pressure", "vibration", "rpm",
        "temperature_roll_avg", "pressure_roll_avg", "vibration_roll_avg", "rpm_roll_avg",
    ]
    readings = db.query(SensorReading).order_by(SensorReading.ts.asc()).all()
    rows = (
        [
            name_by_id.get(r.machine_id, r.machine_id),
            r.ts.isoformat(),
            r.temperature, r.pressure, r.vibration, r.rpm,
            r.temperature_roll_avg, r.pressure_roll_avg, r.vibration_roll_avg, r.rpm_roll_avg,
        ]
        for r in readings
    )
    return _csv_response(header, rows, "pdm_sensors.csv")


@router.get("/anomalies.csv")
def export_anomalies(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    name_by_id = {m.id: m.name for m in db.query(Machine).all()}
    header = ["machine", "parameter", "timestamp", "value", "z_score", "severity", "is_trending"]
    anomalies = db.query(Anomaly).order_by(Anomaly.ts.asc()).all()
    rows = (
        [
            name_by_id.get(a.machine_id, a.machine_id),
            a.parameter, a.ts.isoformat(), a.value,
            round(a.z_score, 3), a.severity, a.is_trending,
        ]
        for a in anomalies
    )
    return _csv_response(header, rows, "pdm_anomalies.csv")


@router.get("/sustainability.csv")
def export_sustainability(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Flat emission-inventory rows for Power BI / ESG reporting, each traceable to
    its activity data and the emission factor used."""
    carbon.seed_factors_if_empty(db)
    carbon.recompute_emissions(db)
    header = [
        "scope", "source_type", "activity_type", "activity_amount", "activity_unit",
        "kgco2e", "cost", "currency", "period_start", "period_end", "data_quality", "origin",
    ]
    records = db.query(EmissionRecord).order_by(EmissionRecord.period_start.asc()).all()
    rows = (
        [
            r.scope, r.source_type, r.activity_type, round(r.activity_amount, 3), r.activity_unit,
            round(r.kgco2e, 3), r.cost, r.currency,
            r.period_start.isoformat(), r.period_end.isoformat(), r.data_quality, r.origin,
        ]
        for r in records
    )
    return _csv_response(header, rows, "pdm_sustainability.csv")
