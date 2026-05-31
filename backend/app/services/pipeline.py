"""Upload processing pipeline: Extract -> Transform -> Load -> Detect -> Track.

Designed to run in a FastAPI BackgroundTask (MVP). The same callable can later be
wrapped as a Celery task (Phase 4) without changes.
"""
import logging

from app.config import settings
from app.anomaly import detect_anomalies
from app.db import SessionLocal
from app.etl import get_engine
from app.ml import log_detection_run
from app.models import Anomaly, Dataset, DatasetStatus, EtlRun, Severity

logger = logging.getLogger(__name__)


def process_dataset(dataset_id: int, csv_path: str) -> None:
    db = SessionLocal()
    try:
        dataset = db.get(Dataset, dataset_id)
        if dataset is None:
            logger.error("Dataset %s not found", dataset_id)
            return
        dataset.status = DatasetStatus.PROCESSING
        db.commit()

        engine = get_engine(settings.etl_engine)
        raw = engine.extract(csv_path)
        transformed = engine.transform(raw)
        summary = engine.load(transformed, dataset_id, db)

        threshold = settings.zscore_threshold
        anomalies = detect_anomalies(transformed, summary["machine_map"], threshold)

        db.bulk_save_objects(
            [Anomaly(dataset_id=dataset_id, **a) for a in anomalies]
        )

        metrics = {
            "rows_processed": summary["row_count"],
            "machines": summary["machine_count"],
            "anomalies_detected": len(anomalies),
            "machines_flagged": len({a["machine_id"] for a in anomalies}),
            "high_severity": sum(1 for a in anomalies if a["severity"] == Severity.HIGH),
        }
        params = {
            "zscore_threshold": threshold,
            "rolling_window": settings.rolling_window,
            "engine": settings.etl_engine,
        }
        run_id = log_detection_run(params, metrics)

        db.add(EtlRun(dataset_id=dataset_id, mlflow_run_id=run_id, params=params, metrics=metrics))
        dataset.row_count = summary["row_count"]
        dataset.status = DatasetStatus.COMPLETED
        db.commit()
        logger.info("Dataset %s processed: %s", dataset_id, metrics)
    except Exception as exc:
        logger.exception("Pipeline failed for dataset %s", dataset_id)
        db.rollback()
        dataset = db.get(Dataset, dataset_id)
        if dataset:
            dataset.status = DatasetStatus.FAILED
            dataset.error = str(exc)[:2000]
            db.commit()
    finally:
        db.close()
