"""Report-generator tests on in-memory SQLite (no Postgres needed)."""
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Framework, UtilityBill, FuelLog
from app.services import carbon, reporting


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, future=True)
    s = Session()
    # A month of grid electricity + a diesel genset, in India.
    s.add(UtilityBill(period_start=datetime(2026, 4, 1), period_end=datetime(2026, 4, 30),
                      kwh=10000.0, cost=80000.0, currency="INR", region="IN"))
    s.add(FuelLog(period_start=datetime(2026, 4, 1), period_end=datetime(2026, 4, 30),
                  fuel_type="diesel", litres=500.0, region="IN"))
    s.commit()
    carbon.recompute_emissions(s)
    try:
        yield s
    finally:
        s.close()


PERIOD = (datetime(2026, 4, 1), datetime(2026, 4, 30))


def test_issb_report_totals(db):
    r = reporting.generate(db, Framework.ISSB, *PERIOD, region="IN")
    s = r.payload["summary"]
    # Scope 2: 10000 * 0.71 = 7100; Scope 1: 500 * 2.68 = 1340.
    assert s["scope2_kgco2e"] == pytest.approx(7100.0, rel=1e-3)
    assert s["scope1_kgco2e"] == pytest.approx(1340.0, rel=1e-3)
    assert s["total_kgco2e"] == pytest.approx(8440.0, rel=1e-3)
    assert r.payload["emission_factors"]  # provenance present
    assert "disclaimer" in r.payload


def test_cbam_intensity(db):
    r = reporting.generate(db, Framework.CBAM, *PERIOD, region="IN", production_tonnes=100.0)
    # total embedded 8440 kg / 100 t = 84.4 kgCO2e per tonne.
    assert r.payload["specific_embedded_emissions"] == pytest.approx(84.4, rel=1e-3)


def test_brsr_energy_in_gj(db):
    r = reporting.generate(db, Framework.BRSR, *PERIOD, region="IN")
    # 10000 kWh * 0.0036 = 36 GJ.
    assert r.payload["summary"]["energy_gj"] == pytest.approx(36.0, rel=1e-3)
    assert r.payload["standard"].startswith("SEBI BRSR")


def test_html_renders(db):
    r = reporting.generate(db, Framework.ISSB, *PERIOD, region="IN")
    html = reporting.render_html(r)
    assert "<html" in html and "Methodology" in html and r.title in html


def test_unknown_framework_falls_back_to_issb(db):
    r = reporting.generate(db, "NONSENSE", *PERIOD, region="IN")
    assert r.framework == Framework.ISSB
