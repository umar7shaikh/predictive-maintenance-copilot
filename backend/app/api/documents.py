import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, get_db
from app.models import DatasetStatus, Document, User
from app.schemas import DocumentOut
from app.security import get_current_user

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _ingest_document(document_id: int, pdf_path: str, source_name: str) -> None:
    from app.rag import ingest_pdf

    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if not doc:
            return
        doc.status = DatasetStatus.PROCESSING
        db.commit()
        count = ingest_pdf(pdf_path, source_name)
        doc.chunk_count = count
        doc.status = DatasetStatus.COMPLETED
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        doc = db.get(Document, document_id)
        if doc:
            doc.status = DatasetStatus.FAILED
            doc.error = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=DocumentOut)
def upload_pdf(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file")

    os.makedirs(settings.upload_dir, exist_ok=True)
    stored = os.path.join(settings.upload_dir, f"{uuid.uuid4().hex}_{file.filename}")
    with open(stored, "wb") as fh:
        fh.write(file.file.read())

    doc = Document(user_id=current.id, filename=file.filename, status=DatasetStatus.PENDING)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background.add_task(_ingest_document, doc.id, stored, file.filename)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    from app.rag import delete_source

    delete_source(doc.filename)  # remove embedded chunks from Chroma
    db.delete(doc)
    db.commit()
