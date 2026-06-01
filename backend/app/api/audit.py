"""Audit-ledger endpoints (Phase 10). Read-only — the ledger is append-only and is
written by the actions it records. Auditors (read-only role) can access this."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditEvent, User
from app.schemas import AuditEventOut
from app.security import get_current_user
from app.services import audit

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventOut])
def list_events(
    limit: int = 200,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return (
        db.query(AuditEvent)
        .order_by(AuditEvent.seq.desc())
        .limit(min(limit, 1000))
        .all()
    )


@router.get("/verify")
def verify(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Recompute the hash chain and report whether the audit trail is intact."""
    return audit.verify_chain(db)
