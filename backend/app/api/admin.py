"""Admin / data-management endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Anomaly,
    ChatMessage,
    Dataset,
    Document,
    EtlRun,
    Machine,
    MaintenanceLog,
    Recommendation,
    SensorReading,
    User,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset")
def reset_data(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Wipe all domain data (keeps user accounts). Also clears the vector store."""
    for model in (
        MaintenanceLog,
        ChatMessage,
        Recommendation,
        Anomaly,
        SensorReading,
        EtlRun,
        Dataset,
        Machine,
        Document,
    ):
        db.query(model).delete(synchronize_session=False)
    db.commit()

    from app.rag import reset_store

    reset_store()
    return {"status": "reset", "by": current.email}
