import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.llm import generate_recommendation
from app.models import Anomaly, ChatMessage, Machine, Recommendation, User
from app.rag import format_context, retrieve
from app.schemas import RecommendRequest, RecommendationOut
from app.security import get_current_user
from app.services.fleet import build_anomaly_summary

router = APIRouter(prefix="/api", tags=["recommendations"])


def _augment_query(db: Session, question: str, machine_id: int | None) -> str:
    """Anomaly-aware query expansion: append the machine name + its anomalous
    parameters so retrieval surfaces the right manual section even for vague
    questions (e.g. 'is it ok?' -> '... PUMP-001 vibration temperature')."""
    terms: list[str] = []
    if machine_id is not None:
        machine = db.get(Machine, machine_id)
        if machine:
            terms.append(machine.name)
            if machine.machine_type:
                terms.append(machine.machine_type)
    params = (
        db.query(Anomaly.parameter)
        .filter(*( [Anomaly.machine_id == machine_id] if machine_id is not None else [] ))
        .distinct()
        .all()
    )
    terms.extend(p[0] for p in params)
    return f"{question} {' '.join(terms)}".strip()


@router.post("/recommend", response_model=RecommendationOut)
def recommend(
    payload: RecommendRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    session_id = payload.session_id or uuid.uuid4().hex
    anomaly_summary = build_anomaly_summary(db, payload.machine_id)

    manual_chunks = (
        retrieve(_augment_query(db, payload.question, payload.machine_id), k=5)
        if payload.use_manuals
        else []
    )
    manual_context = format_context(manual_chunks)

    history = [
        {"role": m.role, "content": m.content}
        for m in db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    ]

    result = generate_recommendation(
        question=payload.question,
        anomaly_summary=anomaly_summary,
        manual_context=manual_context,
        history=history,
    )
    # Use the actually-retrieved chunks as the authoritative citations (clean
    # source + page); fall back to the model's self-reported ones only if none.
    citations = manual_chunks or result.get("citations") or []

    rec = Recommendation(
        user_id=current.id,
        machine_id=payload.machine_id,
        session_id=session_id,
        question=payload.question,
        verdict=result["verdict"],
        explanation=result["explanation"],
        citations=citations,
    )
    db.add(rec)
    db.add(ChatMessage(session_id=session_id, role="user", content=payload.question))
    db.add(
        ChatMessage(
            session_id=session_id,
            role="assistant",
            content=f"[{result['verdict']}] {result['explanation']}",
        )
    )
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/recommendations", response_model=list[RecommendationOut])
def list_recommendations(
    db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return (
        db.query(Recommendation)
        .filter(Recommendation.user_id == current.id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )
