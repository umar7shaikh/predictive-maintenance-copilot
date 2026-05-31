"""MLflow experiment tracking for anomaly-detection runs.

Uses a local file store by default (settings.mlflow_tracking_uri = file:./mlruns),
so it runs natively on Windows with no tracking server required.
"""
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def log_detection_run(params: dict, metrics: dict) -> str | None:
    """Log a detection run to MLflow; returns the run id (or None on failure)."""
    try:
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment)
        with mlflow.start_run() as run:
            mlflow.log_params(params)
            mlflow.log_metrics({k: float(v) for k, v in metrics.items()})
            return run.info.run_id
    except Exception as exc:  # never let telemetry break the pipeline
        logger.warning("MLflow logging failed: %s", exc)
        return None
