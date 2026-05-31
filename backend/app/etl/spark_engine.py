"""PySpark implementation of the ETL pipeline.

Mirrors PandasETLEngine's transforms using Spark SQL window functions, then
returns a pandas DataFrame from transform() so the rest of the pipeline
(load + anomaly detection) stays engine-agnostic. Selected via ETL_ENGINE=spark.

On native Windows, Spark needs JAVA_HOME and a HADOOP_HOME containing winutils;
configure these in .env (see app.config) — they're applied here before Spark starts.
"""
import os
import sys

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.etl.base import ETLEngine, PARAMETERS, REQUIRED_COLUMNS
from app.etl.pandas_engine import PandasETLEngine

_spark_session = None


def _configure_env() -> None:
    if settings.java_home:
        os.environ.setdefault("JAVA_HOME", settings.java_home)
    if settings.hadoop_home:
        os.environ["HADOOP_HOME"] = settings.hadoop_home
        os.environ["PATH"] = (
            os.path.join(settings.hadoop_home, "bin") + os.pathsep + os.environ.get("PATH", "")
        )
    # Driver and workers must use the same interpreter (this venv).
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)


def get_spark():
    global _spark_session
    if _spark_session is None:
        _configure_env()
        from pyspark.sql import SparkSession

        _spark_session = (
            SparkSession.builder.appName("pdm-etl")
            .master("local[*]")
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.ui.enabled", "false")
            .config("spark.driver.memory", "1g")
            .getOrCreate()
        )
        _spark_session.sparkContext.setLogLevel("ERROR")
    return _spark_session


class SparkETLEngine(ETLEngine):
    def __init__(self, rolling_window: int | None = None):
        self.rolling_window = rolling_window or settings.rolling_window
        self._loader = PandasETLEngine(self.rolling_window)  # reuse persistence

    # ---------- Extract ----------
    def extract(self, csv_path: str):
        spark = get_spark()
        sdf = spark.read.option("header", True).option("inferSchema", True).csv(csv_path)
        sdf = sdf.toDF(*[c.strip().lower() for c in sdf.columns])
        missing = [c for c in REQUIRED_COLUMNS if c not in sdf.columns]
        if missing:
            raise ValueError(
                f"CSV is missing required column(s): {', '.join(missing)}. "
                f"Expected columns: {', '.join(REQUIRED_COLUMNS)}."
            )
        return sdf

    # ---------- Transform (returns pandas) ----------
    def transform(self, sdf) -> pd.DataFrame:
        from pyspark.sql import Window
        from pyspark.sql import functions as F

        sdf = sdf.withColumn("timestamp", F.to_timestamp("timestamp"))
        sdf = sdf.withColumn("machine_id", F.trim(F.col("machine_id").cast("string")))
        sdf = sdf.filter(F.col("timestamp").isNotNull() & (F.col("machine_id") != ""))
        for p in PARAMETERS:
            sdf = sdf.withColumn(p, F.col(p).cast("double"))

        order = Window.partitionBy("machine_id").orderBy("timestamp")
        ffill = order.rowsBetween(Window.unboundedPreceding, 0)
        bfill = order.rowsBetween(0, Window.unboundedFollowing)
        roll = order.rowsBetween(-(self.rolling_window - 1), 0)

        for p in PARAMETERS:
            # Null handling: forward-fill, then back-fill within each machine.
            sdf = sdf.withColumn(p, F.last(p, ignorenulls=True).over(ffill))
            sdf = sdf.withColumn(p, F.first(p, ignorenulls=True).over(bfill))
            # Engineered features.
            sdf = sdf.withColumn(f"{p}_roll_avg", F.avg(p).over(roll))
            sdf = sdf.withColumn(f"{p}_roc", F.col(p) - F.lag(p, 1).over(order))
            sdf = sdf.fillna({f"{p}_roc": 0.0})

        pdf = sdf.toPandas()
        pdf["timestamp"] = pd.to_datetime(pdf["timestamp"])
        return pdf.sort_values(["machine_id", "timestamp"]).reset_index(drop=True)

    # ---------- Load (delegates to the shared pandas loader) ----------
    def load(self, df: pd.DataFrame, dataset_id: int, db: Session) -> dict:
        return self._loader.load(df, dataset_id, db)
