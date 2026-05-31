"""Statistical (z-score) anomaly detection with severity and trend scoring."""
import numpy as np
import pandas as pd

from app.etl.base import PARAMETERS
from app.models import Severity


def severity_for(abs_z: float, threshold: float) -> str:
    """Map an absolute z-score to a severity bucket, relative to the threshold."""
    if abs_z >= threshold * 1.5:
        return Severity.HIGH
    if abs_z >= threshold * 1.2:
        return Severity.MEDIUM
    return Severity.MONITOR


def _trend_slope(values: np.ndarray) -> float:
    """Normalized linear-regression slope; >0 means the parameter is rising."""
    n = len(values)
    if n < 3:
        return 0.0
    std = values.std()
    if std == 0:
        return 0.0
    x = np.arange(n)
    slope = np.polyfit(x, values, 1)[0]
    # Normalize so the value is comparable across parameters/scales.
    return float(slope * n / std)


def detect_anomalies(
    df: pd.DataFrame,
    machine_map: dict[str, int],
    threshold: float,
) -> list[dict]:
    """Detect anomalies on the transformed dataframe.

    Returns a list of dicts ready to build Anomaly rows. Operates per machine and
    per parameter using a z-score over each machine's series.
    """
    anomalies: list[dict] = []

    for machine_name, group in df.groupby("machine_id"):
        machine_id = machine_map[machine_name]
        for param in PARAMETERS:
            series = group[param].astype(float)
            if series.notna().sum() < 3:
                continue
            mean = series.mean()
            std = series.std()
            if not std or np.isnan(std) or std == 0:
                continue

            slope = _trend_slope(series.dropna().to_numpy())
            is_trending = abs(slope) >= 1.0

            zscores = (series - mean) / std
            flagged = group[zscores.abs() >= threshold]
            flagged_z = zscores[zscores.abs() >= threshold]

            for (_, row), z in zip(flagged.iterrows(), flagged_z):
                anomalies.append(
                    {
                        "machine_id": machine_id,
                        "parameter": param,
                        "ts": row["timestamp"].to_pydatetime(),
                        "value": float(row[param]),
                        "z_score": float(z),
                        "severity": severity_for(abs(float(z)), threshold),
                        "is_trending": bool(is_trending),
                        "trend_slope": slope,
                    }
                )

    return anomalies
