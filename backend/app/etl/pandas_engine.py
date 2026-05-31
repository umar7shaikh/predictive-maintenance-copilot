"""pandas implementation of the ETL pipeline (Extract -> Transform -> Load)."""
import pandas as pd

from sqlalchemy.orm import Session

from app.config import settings
from app.etl.base import ETLEngine, PARAMETERS, REQUIRED_COLUMNS
from app.models import Machine, SensorReading


class PandasETLEngine(ETLEngine):
    def __init__(self, rolling_window: int | None = None):
        self.rolling_window = rolling_window or settings.rolling_window

    # ---------- Extract ----------
    def extract(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df.columns = [c.strip().lower() for c in df.columns]
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"CSV is missing required column(s): {', '.join(missing)}. "
                f"Expected columns: {', '.join(REQUIRED_COLUMNS)}."
            )
        return df

    # ---------- Transform ----------
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Parse timestamps; drop rows with an unparseable time or no machine id.
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["machine_id"] = df["machine_id"].astype(str).str.strip()
        df = df.dropna(subset=["timestamp"])
        df = df[df["machine_id"] != ""]

        # Coerce sensor columns to numeric.
        for p in PARAMETERS:
            df[p] = pd.to_numeric(df[p], errors="coerce")

        # Unit normalization: if temperature is supplied in Fahrenheit
        # (optional 'temp_unit' column), convert to Celsius.
        if "temp_unit" in df.columns:
            mask_f = df["temp_unit"].astype(str).str.upper().str.startswith("F")
            df.loc[mask_f, "temperature"] = (df.loc[mask_f, "temperature"] - 32) * 5.0 / 9.0

        df = df.sort_values(["machine_id", "timestamp"]).reset_index(drop=True)

        # Null handling: ffill/bfill within each machine, then median per machine.
        grp = df.groupby("machine_id")
        for p in PARAMETERS:
            df[p] = grp[p].ffill()
            df[p] = df.groupby("machine_id")[p].bfill()
            df[p] = df[p].fillna(df.groupby("machine_id")[p].transform("median"))

        # Feature engineering per machine: rolling average + rate-of-change.
        w = self.rolling_window
        for p in PARAMETERS:
            df[f"{p}_roll_avg"] = df.groupby("machine_id")[p].transform(
                lambda s: s.rolling(window=w, min_periods=1).mean()
            )
            df[f"{p}_roc"] = df.groupby("machine_id")[p].transform(
                lambda s: s.diff().fillna(0.0)
            )

        return df

    # ---------- Load ----------
    def load(self, df: pd.DataFrame, dataset_id: int, db: Session) -> dict:
        machine_map: dict[str, int] = {}
        for name in df["machine_id"].unique():
            machine = db.query(Machine).filter(Machine.name == name).first()
            if machine is None:
                machine = Machine(name=name, machine_type=_infer_type(name))
                db.add(machine)
                db.flush()  # assign id
            machine_map[name] = machine.id

        readings: list[SensorReading] = []
        for row in df.itertuples(index=False):
            r = SensorReading(
                machine_id=machine_map[row.machine_id],
                dataset_id=dataset_id,
                ts=row.timestamp.to_pydatetime(),
            )
            for p in PARAMETERS:
                setattr(r, p, _f(getattr(row, p)))
                setattr(r, f"{p}_roll_avg", _f(getattr(row, f"{p}_roll_avg")))
                setattr(r, f"{p}_roc", _f(getattr(row, f"{p}_roc")))
            readings.append(r)

        db.bulk_save_objects(readings)
        db.commit()

        return {
            "machine_map": machine_map,
            "machine_count": len(machine_map),
            "row_count": len(readings),
        }


def _f(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _infer_type(name: str) -> str:
    n = name.lower()
    if "pump" in n:
        return "Hydraulic Pump"
    if "motor" in n:
        return "Motor"
    if "valve" in n:
        return "Valve"
    return "Equipment"
