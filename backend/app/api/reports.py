"""Regulatory report endpoints (Phase 8)."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Framework, RegulatoryReport, Role, User
from app.schemas import (
    RegulatoryReportDetail,
    RegulatoryReportOut,
    ReportGenerateRequest,
)
from app.security import get_current_user, require_role
from app.services import audit, reporting

router = APIRouter(prefix="/api/reports", tags=["reports"])

_FRAMEWORKS = {Framework.ISSB, Framework.CBAM, Framework.BRSR}


@router.get("/frameworks")
def frameworks(current: User = Depends(get_current_user)):
    return [
        {"id": Framework.ISSB, "name": "ISSB / GHG Protocol", "desc": "Neutral climate-disclosure baseline (IFRS S2)."},
        {"id": Framework.CBAM, "name": "EU CBAM", "desc": "Embedded emissions of goods exported to the EU."},
        {"id": Framework.BRSR, "name": "India BRSR", "desc": "SEBI Principle 6 — environment disclosure."},
    ]


@router.post("/generate", response_model=RegulatoryReportDetail)
def generate(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current: User = Depends(require_role(Role.OPERATOR)),  # auditors are read-only
):
    if payload.framework not in _FRAMEWORKS:
        raise HTTPException(status_code=422, detail=f"Unknown framework: {payload.framework}")
    if payload.period_end <= payload.period_start:
        raise HTTPException(status_code=422, detail="period_end must be after period_start")
    report = reporting.generate(
        db,
        framework=payload.framework,
        period_start=payload.period_start,
        period_end=payload.period_end,
        region=payload.region,
        production_tonnes=payload.production_tonnes,
    )
    # Record an immutable audit event for assurance.
    summ = (report.payload or {}).get("summary", {})
    audit.record(
        db,
        event_type="report.generate",
        summary=f"Generated {report.framework} report '{report.title}' "
                f"({report.period_start:%Y-%m-%d}→{report.period_end:%Y-%m-%d}): "
                f"{summ.get('total_tonnes_co2e', 0)} tCO2e",
        entity="regulatory_report",
        entity_id=report.id,
        actor=current.email,
        data={"framework": report.framework, "region": report.region,
              "total_tonnes_co2e": summ.get("total_tonnes_co2e")},
    )
    return report


@router.get("", response_model=list[RegulatoryReportOut])
def list_reports(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(RegulatoryReport).order_by(RegulatoryReport.created_at.desc()).all()


@router.get("/{report_id}", response_model=RegulatoryReportDetail)
def get_report(
    report_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    report = db.get(RegulatoryReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/html", response_class=HTMLResponse)
def get_report_html(
    report_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    report = db.get(RegulatoryReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(content=reporting.render_html(report))


@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    report = db.get(RegulatoryReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
