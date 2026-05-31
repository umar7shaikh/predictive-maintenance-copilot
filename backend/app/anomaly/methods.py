"""Pluggable anomaly-detection algorithms.

All methods share one signature and output shape so they're interchangeable and
comparable side-by-side in MLflow. Each flags points and assigns a severity.

Operates on a DataFrame with columns: machine_id, dataset_id, ts + the params.
Each per-series method returns a dict {row_index: (score, severity)} for flagged
points, where `score` is a z-like magnitude stored for display.
"""
import logging

import numpy as np
import pandas as pd

from app.anomaly.detector import _trend_slope
from app.etl.base import PARAMETERS
from app.models import Severity

logger = logging.getLogger(__name__)

METHODS = ["zscore", "rolling_z", "ewma", "iqr", "isolation_forest"]


def _sev(score: float, threshold: float) -> str:
    if score >= threshold * 1.5:
        return Severity.HIGH
    if score >= threshold * 1.2:
        return Severity.MEDIUM
    return Severity.MONITOR


def _flag_zlike(scores: pd.Series, threshold: float) -> dict:
    out = {}
    for idx, s in scores.items():
        if pd.notna(s) and s >= threshold:
            out[idx] = (float(s), _sev(float(s), threshold))
    return out


def _evaluate(series: pd.Series, method: str, threshold: float, window: int) -> dict:
    x = series.astype(float)

    if method == "zscore":
        std = x.std()
        if not std:
            return {}
        return _flag_zlike((x - x.mean()).abs() / std, threshold)

    if method == "rolling_z":
        # Compare each point to a TRAILING baseline (excludes the point itself),
        # so an isolated spike stands out instead of inflating its own window.
        base = x.shift(1)
        rmean = base.rolling(window, min_periods=max(3, window // 2)).mean()
        rstd = base.rolling(window, min_periods=max(3, window // 2)).std()
        scores = ((x - rmean) / rstd).abs().replace([np.inf, -np.inf], np.nan)
        return _flag_zlike(scores, threshold)

    if method == "ewma":
        ewm = x.ewm(span=window, adjust=False).mean()
        resid = (x - ewm).abs()
        std = resid.std()
        if not std:
            return {}
        return _flag_zlike(resid / std, threshold)

    if method == "iqr":
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        if not iqr:
            return {}
        k = max(0.5, threshold / 2.0)  # shared slider -> IQR multiplier
        lower, upper = q1 - k * iqr, q3 + k * iqr
        dist = pd.concat([(lower - x), (x - upper)], axis=1).max(axis=1) / iqr
        out = {}
        for idx, d in dist.items():
            if pd.notna(d) and d > 0:
                sev = Severity.HIGH if d >= 1.5 else Severity.MEDIUM if d >= 0.75 else Severity.MONITOR
                out[idx] = (float(d), sev)
        return out

    if method == "isolation_forest":
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            logger.warning("scikit-learn missing; falling back to zscore")
            return _evaluate(series, "zscore", threshold, window)
        vals = x.to_numpy().reshape(-1, 1)
        contamination = float(min(0.25, max(0.005, 0.02 * threshold)))
        model = IsolationForest(contamination=contamination, random_state=0, n_estimators=120)
        preds = model.fit_predict(vals)            # -1 = anomaly
        raw = -model.score_samples(vals)           # higher = more anomalous
        rstd = raw.std() or 1.0
        zlike = (raw - raw.mean()) / rstd
        out = {}
        for i, idx in enumerate(x.index):
            if preds[i] == -1:
                score = abs(float(zlike[i]))
                sev = Severity.HIGH if score >= 1.5 else Severity.MEDIUM if score >= 0.75 else Severity.MONITOR
                out[idx] = (max(score, 0.5), sev)
        return out

    raise ValueError(f"Unknown method: {method}")


def detect(df: pd.DataFrame, method: str, threshold: float, window: int) -> list[dict]:
    if method not in METHODS:
        raise ValueError(f"Unknown method: {method}")

    anomalies: list[dict] = []
    for machine_id, group in df.groupby("machine_id"):
        for param in PARAMETERS:
            series = group[param]
            if series.notna().sum() < 5:
                continue
            flags = _evaluate(series, method, threshold, window)
            if not flags:
                continue
            slope = _trend_slope(series.dropna().to_numpy())
            is_trending = abs(slope) >= 1.0
            for idx, (score, severity) in flags.items():
                row = group.loc[idx]
                anomalies.append(
                    {
                        "machine_id": int(machine_id),
                        "dataset_id": int(row["dataset_id"]),
                        "parameter": param,
                        "ts": row["ts"].to_pydatetime(),
                        "value": float(row[param]),
                        "z_score": float(score),
                        "severity": severity,
                        "is_trending": bool(is_trending),
                        "trend_slope": slope,
                    }
                )
    return anomalies
