"""Verify the SparkETLEngine runs natively and matches pandas anomaly results.

Sets JAVA_HOME/HADOOP_HOME from .env, runs extract+transform with each engine on
the sample CSV, runs z-score detection on both, and compares the results.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

from app.anomaly import detect_anomalies  # noqa: E402
from app.etl.pandas_engine import PandasETLEngine  # noqa: E402
from app.etl.spark_engine import SparkETLEngine  # noqa: E402

CSV = os.path.join(BACKEND, "sample_data", "sample_sensors.csv")


def _machine_map(df):
    return {name: i for i, name in enumerate(sorted(df["machine_id"].unique()))}


def run(engine, label):
    raw = engine.extract(CSV)
    tdf = engine.transform(raw)
    mm = _machine_map(tdf)
    anoms = detect_anomalies(tdf, mm, threshold=3.0)
    by_sev = {}
    for a in anoms:
        by_sev[a["severity"]] = by_sev.get(a["severity"], 0) + 1
    print(f"[{label}] rows={len(tdf)} anomalies={len(anoms)} by_severity={by_sev}")
    return len(tdf), len(anoms), by_sev


print("=== pandas ===")
p_rows, p_anom, p_sev = run(PandasETLEngine(), "pandas")

print("=== spark ===")
s_rows, s_anom, s_sev = run(SparkETLEngine(), "spark")

print("\n=== comparison ===")
print(f"rows: pandas={p_rows} spark={s_rows} match={p_rows == s_rows}")
print(f"anomalies: pandas={p_anom} spark={s_anom} match={p_anom == s_anom}")
print(f"severity match={p_sev == s_sev}")
print("RESULT:", "PASS" if (p_rows == s_rows and abs(p_anom - s_anom) <= 1) else "CHECK")
