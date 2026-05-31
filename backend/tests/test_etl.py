import pandas as pd
import pytest

from app.etl.pandas_engine import PandasETLEngine


def _raw_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=6, freq="h"),
            "machine_id": ["M1"] * 6,
            "temperature": [60, 61, None, 63, 64, 65],
            "pressure": [100, 101, 102, 103, 104, 105],
            "vibration": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
            "rpm": [1500] * 6,
        }
    )


def test_extract_rejects_missing_columns(tmp_path):
    csv = tmp_path / "bad.csv"
    pd.DataFrame({"timestamp": [1], "machine_id": ["M1"]}).to_csv(csv, index=False)
    engine = PandasETLEngine()
    with pytest.raises(ValueError, match="missing required column"):
        engine.extract(str(csv))


def test_transform_fills_nulls_and_adds_features():
    engine = PandasETLEngine(rolling_window=3)
    out = engine.transform(_raw_df())

    assert out["temperature"].isna().sum() == 0  # null handled
    for col in ("temperature_roll_avg", "temperature_roc"):
        assert col in out.columns
    # rate-of-change first row is 0 by construction
    assert out.iloc[0]["temperature_roc"] == 0.0


def test_fahrenheit_normalized_to_celsius():
    engine = PandasETLEngine()
    df = _raw_df()
    df["temp_unit"] = "F"
    df["temperature"] = [140, 140, 140, 140, 140, 140]  # 60 C
    out = engine.transform(df)
    assert out["temperature"].round(1).iloc[0] == 60.0
