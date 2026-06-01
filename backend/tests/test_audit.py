"""Audit-ledger tamper-evidence tests (in-memory SQLite)."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import AuditEvent
from app.services import audit


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.close()


def test_chain_links_and_verifies(db):
    a = audit.record(db, "report.generate", "first", actor="u@x.io", data={"n": 1})
    b = audit.record(db, "report.generate", "second", actor="u@x.io", data={"n": 2})
    assert a.prev_hash == audit.GENESIS
    assert b.prev_hash == a.hash          # chained
    assert b.seq == 2
    result = audit.verify_chain(db)
    assert result["valid"] is True
    assert result["events"] == 2


def test_tampering_breaks_verification(db):
    audit.record(db, "emissions.recompute", "run 1", data={"kwh": 100})
    audit.record(db, "emissions.recompute", "run 2", data={"kwh": 200})
    # Tamper with a stored event's content directly (bypassing record()).
    db.execute(text("UPDATE audit_events SET summary = 'EDITED' WHERE seq = 1"))
    db.commit()
    result = audit.verify_chain(db)
    assert result["valid"] is False
    assert result["broken_at"] == 1


def test_deletion_breaks_verification(db):
    audit.record(db, "x", "1")
    audit.record(db, "x", "2")
    audit.record(db, "x", "3")
    db.execute(text("DELETE FROM audit_events WHERE seq = 2"))
    db.commit()
    result = audit.verify_chain(db)
    assert result["valid"] is False  # sequence gap / broken link


def test_empty_chain_is_valid(db):
    assert audit.verify_chain(db)["valid"] is True
