"""Celery application + async tasks for heavy work (ETL, PDF ingestion).

On Windows run the worker with the solo pool:
    celery -A app.worker.celery_app worker --loglevel=info --pool=solo

When settings.use_celery is False, the API calls the same underlying functions
via FastAPI BackgroundTasks instead, so Celery is fully optional.
"""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "pdm_copilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_max_tasks_per_child=20,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="process_dataset")
def process_dataset_task(dataset_id: int, csv_path: str) -> dict:
    from app.services.pipeline import process_dataset

    process_dataset(dataset_id, csv_path)
    return {"dataset_id": dataset_id, "status": "done"}


@celery_app.task(name="ingest_document")
def ingest_document_task(document_id: int, pdf_path: str, source_name: str) -> dict:
    from app.api.documents import _ingest_document

    _ingest_document(document_id, pdf_path, source_name)
    return {"document_id": document_id, "status": "done"}
