import numpy as np
import pandas as pd

from app.anomaly.detector import detect_anomalies, severity_for
from app.models import Severity


def test_severity_buckets():
    assert severity_for(5.0, 3.0) == Severity.HIGH      # >= 4.5
    assert severity_for(3.8, 3.0) == Severity.MEDIUM     # >= 3.6
    assert severity_for(3.1, 3.0) == Severity.MONITOR    # >= 3.0


def test_detects_injected_spike():
    n = 60
    temp = np.full(n, 60.0) + np.random.default_rng(0).normal(0, 0.5, n)
    temp[55] = 120.0  # obvious spike
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="h"),
            "machine_id": ["M1"] * n,
            "temperature": temp,
            "pressure": np.full(n, 100.0),
            "vibration": np.full(n, 1.0),
            "rpm": np.full(n, 1500.0),
        }
    )
    anomalies = detect_anomalies(df, {"M1": 1}, threshold=3.0)
    temp_anoms = [a for a in anomalies if a["parameter"] == "temperature"]
    assert any(a["value"] == 120.0 for a in temp_anoms)
    assert temp_anoms[0]["severity"] in {Severity.HIGH, Severity.MEDIUM, Severity.MONITOR}


def test_no_anomalies_on_flat_signal():
    n = 40
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="h"),
            "machine_id": ["M1"] * n,
            "temperature": np.full(n, 60.0),
            "pressure": np.full(n, 100.0),
            "vibration": np.full(n, 1.0),
            "rpm": np.full(n, 1500.0),
        }
    )
    assert detect_anomalies(df, {"M1": 1}, threshold=3.0) == []
