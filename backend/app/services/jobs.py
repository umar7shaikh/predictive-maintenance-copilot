"""Job dispatch: route heavy work to Celery when enabled, else BackgroundTasks.

Keeps a single decision point so endpoints don't branch on the toggle.
"""
import logging

from fastapi import BackgroundTasks

from app.config import settings

logger = logging.getLogger(__name__)


def dispatch_dataset(background: BackgroundTasks, dataset_id: int, csv_path: str) -> str:
    if settings.use_celery:
        try:
            from app.worker import process_dataset_task

            process_dataset_task.delay(dataset_id, csv_path)
            return "celery"
        except Exception as exc:  # broker down -> fall back gracefully
            logger.warning("Celery dispatch failed (%s); using BackgroundTasks.", exc)

    from app.services.pipeline import process_dataset

    background.add_task(process_dataset, dataset_id, csv_path)
    return "background"


def dispatch_document(
    background: BackgroundTasks, document_id: int, pdf_path: str, source_name: str
) -> str:
    if settings.use_celery:
        try:
            from app.worker import ingest_document_task

            ingest_document_task.delay(document_id, pdf_path, source_name)
            return "celery"
        except Exception as exc:
            logger.warning("Celery dispatch failed (%s); using BackgroundTasks.", exc)

    from app.api.documents import _ingest_document

    background.add_task(_ingest_document, document_id, pdf_path, source_name)
    return "background"
