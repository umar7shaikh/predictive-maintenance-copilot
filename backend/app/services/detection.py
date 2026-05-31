"""Re-run anomaly detection over already-ingested readings with tunable params.

Lets engineers tune the z-threshold / window / algorithm and immediately see the
effect, with every run logged to MLflow + the etl_runs table for comparison.
"""
import logging

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.anomaly.methods import detect
from app.etl.base import PARAMETERS
from app.ml import log_detection_run
from app.models import Anomaly, Dataset, EtlRun, SensorReading, Severity

logger = logging.getLogger(__name__)


def _load_readings_df(db: Session) -> pd.DataFrame:
    rows = db.query(
        SensorReading.machine_id,
        SensorReading.dataset_id,
        SensorReading.ts,
        SensorReading.temperature,
        SensorReading.pressure,
        SensorReading.vibration,
        SensorReading.rpm,
    ).order_by(SensorReading.machine_id, SensorReading.ts).all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows, columns=["machine_id", "dataset_id", "ts", *PARAMETERS])


def rerun_detection(db: Session, method: str, threshold: float, window: int) -> dict:
    df = _load_readings_df(db)
    if df.empty:
        return {"error": "No sensor data to analyze. Upload a CSV first."}

    df["ts"] = pd.to_datetime(df["ts"])
    anomalies = detect(df, method=method, threshold=threshold, window=window)

    # Replace the current anomaly set with the new run's results.
    db.query(Anomaly).delete(synchronize_session=False)
    db.bulk_save_objects([Anomaly(**a) for a in anomalies])

    metrics = {
        "rows_analyzed": int(len(df)),
        "machines": int(df["machine_id"].nunique()),
        "anomalies_detected": len(anomalies),
        "machines_flagged": len({a["machine_id"] for a in anomalies}),
        "high_severity": sum(1 for a in anomalies if a["severity"] == Severity.HIGH),
    }
    params = {"method": method, "threshold": threshold, "window": window}
    run_id = log_detection_run(params, metrics)

    latest_dataset = db.query(func.max(Dataset.id)).scalar()
    if latest_dataset:
        db.add(EtlRun(dataset_id=latest_dataset, mlflow_run_id=run_id, params=params, metrics=metrics))
    db.commit()

    return {"mlflow_run_id": run_id, "params": params, "metrics": metrics}
