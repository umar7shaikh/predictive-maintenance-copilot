"""Append-only, hash-chained audit ledger (Phase 10).

Tamper-evidence: each event's hash is SHA-256 over its canonical content plus the
previous event's hash. Re-deriving the chain detects any insertion, deletion, or
edit of a past event — the property external assurers (BRSR Core, CBAM) rely on.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditEvent

GENESIS = "0" * 64


def _canonical(seq: int, event_type: str, entity, entity_id, summary: str,
               actor, created_at_iso: str, data) -> str:
    """Deterministic JSON of the hashed fields (sorted keys, no whitespace drift)."""
    return json.dumps(
        {
            "seq": seq,
            "event_type": event_type,
            "entity": entity,
            "entity_id": entity_id,
            "summary": summary,
            "actor": actor,
            "created_at": created_at_iso,
            "data": data,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _digest(prev_hash: str, content: str) -> str:
    return hashlib.sha256((prev_hash + content).encode("utf-8")).hexdigest()


def record(
    db: Session,
    event_type: str,
    summary: str,
    *,
    entity: str | None = None,
    entity_id: int | None = None,
    actor: str | None = None,
    data: dict | None = None,
) -> AuditEvent:
    """Append a new event to the ledger and return it."""
    last = db.query(AuditEvent).order_by(AuditEvent.seq.desc()).first()
    seq = (last.seq + 1) if last else 1
    prev_hash = last.hash if last else GENESIS
    created_at = datetime.utcnow()
    created_iso = created_at.isoformat()

    content = _canonical(seq, event_type, entity, entity_id, summary, actor, created_iso, data)
    h = _digest(prev_hash, content)

    ev = AuditEvent(
        seq=seq, event_type=event_type, entity=entity, entity_id=entity_id,
        summary=summary, actor=actor, data=data,
        prev_hash=prev_hash, hash=h, created_at=created_at,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def verify_chain(db: Session) -> dict:
    """Recompute the whole chain and report integrity."""
    events = db.query(AuditEvent).order_by(AuditEvent.seq.asc()).all()
    prev = GENESIS
    for i, ev in enumerate(events, start=1):
        if ev.seq != i:
            return {"valid": False, "events": len(events),
                    "broken_at": ev.seq, "reason": "sequence gap or reorder"}
        if ev.prev_hash != prev:
            return {"valid": False, "events": len(events),
                    "broken_at": ev.seq, "reason": "prev_hash mismatch"}
        content = _canonical(ev.seq, ev.event_type, ev.entity, ev.entity_id,
                             ev.summary, ev.actor, ev.created_at.isoformat(), ev.data)
        if _digest(ev.prev_hash, content) != ev.hash:
            return {"valid": False, "events": len(events),
                    "broken_at": ev.seq, "reason": "content hash mismatch (tampered)"}
        prev = ev.hash
    return {"valid": True, "events": len(events), "head": prev if events else GENESIS}
