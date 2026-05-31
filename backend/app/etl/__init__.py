from app.etl.base import ETLEngine
from app.etl.pandas_engine import PandasETLEngine

__all__ = ["ETLEngine", "PandasETLEngine", "get_engine"]


def get_engine(name: str = "pandas") -> ETLEngine:
    """Factory so a SparkETLEngine can be swapped in later via config."""
    if name == "pandas":
        return PandasETLEngine()
    raise ValueError(f"Unknown ETL engine: {name}")
