from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatMessage, User
from app.schemas import ChatMessageOut
from app.security import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/{session_id}", response_model=list[ChatMessageOut])
def get_session(
    session_id: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
