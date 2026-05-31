from app.etl.base import ETLEngine
from app.etl.pandas_engine import PandasETLEngine

__all__ = ["ETLEngine", "PandasETLEngine", "get_engine"]


def get_engine(name: str = "pandas") -> ETLEngine:
    """Factory: select the ETL engine implementation by name."""
    if name == "pandas":
        return PandasETLEngine()
    if name == "spark":
        from app.etl.spark_engine import SparkETLEngine

        return SparkETLEngine()
    raise ValueError(f"Unknown ETL engine: {name}")
