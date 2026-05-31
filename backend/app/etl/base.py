"""ETL engine interface.

The MVP ships a pandas implementation. A PySpark implementation can be added later
against this same contract (see plan Phase 4) without touching callers.
"""
from abc import ABC, abstractmethod

import pandas as pd
from sqlalchemy.orm import Session

# Canonical sensor parameters handled across the pipeline.
PARAMETERS = ["temperature", "pressure", "vibration", "rpm"]
REQUIRED_COLUMNS = ["timestamp", "machine_id", *PARAMETERS]


class ETLEngine(ABC):
    @abstractmethod
    def extract(self, csv_path: str) -> pd.DataFrame:
        """Read and validate the raw CSV."""

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean + engineer features (nulls, units, rolling avg, rate-of-change)."""

    @abstractmethod
    def load(self, df: pd.DataFrame, dataset_id: int, db: Session) -> dict:
        """Persist processed readings; return summary incl. machine id mapping."""
