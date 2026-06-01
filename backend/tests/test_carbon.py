"""Carbon engine tests — self-contained on in-memory SQLite (no Postgres needed)."""
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Anomaly,
    Machine,
    SensorReading,
    Severity,
    UtilityBill,
    FuelLog,
)
from app.services import carbon


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.close()


def test_seed_factors_idempotent(db):
    n1 = carbon.seed_factors_if_empty(db)
    n2 = carbon.seed_factors_if_empty(db)
    assert n1 > 0
    assert n2 == 0  # second call is a no-op


def test_grid_factor_falls_back_to_global(db):
    carbon.seed_factors_if_empty(db)
    # An unknown region has no specific row -> GLOBAL fallback is returned.
    f = carbon.get_factor(db, "ZZ", "grid_electricity")
    assert f is not None and f.region == "GLOBAL"
    # A known region returns its own row.
    f_in = carbon.get_factor(db, "IN", "grid_electricity")
    assert f_in.region == "IN"


def test_scope2_from_utility_bill(db):
    carbon.seed_factors_if_empty(db)
    db.add(UtilityBill(
        period_start=datetime(2026, 4, 1), period_end=datetime(2026, 4, 30),
        kwh=10000.0, cost=80000.0, currency="INR", region="IN",
    ))
    db.commit()
    carbon.recompute_emissions(db)
    summ = carbon.emissions_summary(db)
    # 10000 kWh * 0.71 (IN grid default) = 7100 kgCO2e, all Scope 2.
    assert summ["scope2_kgco2e"] == pytest.approx(7100.0, rel=1e-3)
    assert summ["scope1_kgco2e"] == 0.0
    assert summ["total_kwh"] == pytest.approx(10000.0)


def test_scope1_diesel_from_runtime_is_estimated(db):
    carbon.seed_factors_if_empty(db)
    # 10 runtime hours, no litres -> estimated via default 20 L/h = 200 L diesel.
    db.add(FuelLog(
        period_start=datetime(2026, 4, 1), period_end=datetime(2026, 4, 2),
        fuel_type="diesel", runtime_hours=10.0, region="IN",
    ))
    db.commit()
    carbon.recompute_emissions(db)
    summ = carbon.emissions_summary(db)
    # 200 L * 2.68 kgCO2e/L = 536 kgCO2e, Scope 1.
    assert summ["scope1_kgco2e"] == pytest.approx(536.0, rel=1e-3)


def test_energy_waste_scales_with_severity(db):
    carbon.seed_factors_if_empty(db)
    m = Machine(name="PUMP-001", machine_type="pump", rated_power_kw=10.0)
    db.add(m)
    db.flush()
    # 100 hours of readings span.
    db.add(SensorReading(machine_id=m.id, dataset_id=1, ts=datetime(2026, 4, 1, 0)))
    db.add(SensorReading(machine_id=m.id, dataset_id=1, ts=datetime(2026, 4, 5, 4)))  # +100h
    db.add(Anomaly(machine_id=m.id, dataset_id=1, parameter="temperature",
                   ts=datetime(2026, 4, 2), value=120.0, z_score=5.0,
                   severity=Severity.HIGH, is_trending=False))
    db.commit()

    w = carbon.estimate_machine_waste(db, m)
    # energy = 10 kW * 100 h = 1000 kWh; HIGH penalty 8% -> 80 kWh wasted.
    assert w["wasted_kwh"] == pytest.approx(80.0, rel=1e-3)
    assert w["wasted_kgco2e"] > 0
    assert w["saveable_cost"] > 0


def test_waste_none_without_rated_power(db):
    carbon.seed_factors_if_empty(db)
    m = Machine(name="VALVE-9")  # no rated_power_kw
    db.add(m)
    db.commit()
    assert carbon.estimate_machine_waste(db, m) is None
