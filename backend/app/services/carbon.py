"""Carbon engine — turns energy activity data into a traceable emission inventory.

Two computation paths:
  * Scope 2 — purchased grid electricity (from UtilityBills, or metered power_kw).
  * Scope 1 — fuel combustion, esp. diesel gensets (from FuelLogs).

Plus the predictive-maintenance link: estimate the energy a degrading machine is
**wasting**, expressed as kWh, CO2, and money — decision-support, never booked
against the inventory.

Every emission number is traceable to the activity data and the EmissionFactor
(with its source) used to compute it.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.carbon.factors import DEFAULT_GENSET_LITRES_PER_HOUR, SEED_FACTORS
from app.config import settings
from app.models import (
    Anomaly,
    DataQuality,
    EmissionFactor,
    EmissionRecord,
    EnergySource,
    FuelLog,
    Machine,
    Severity,
    UtilityBill,
)


# --- reference data -------------------------------------------------------

def seed_factors_if_empty(db: Session) -> int:
    """Insert the default emission factors once. Returns rows inserted."""
    if db.query(EmissionFactor).count() > 0:
        return 0
    for f in SEED_FACTORS:
        db.add(EmissionFactor(**f))
    db.commit()
    return len(SEED_FACTORS)


def get_factor(db: Session, region: str, activity_type: str) -> EmissionFactor | None:
    """Best emission factor for a region/activity, falling back to GLOBAL.

    Prefers a region-specific row; otherwise the GLOBAL default. Among matches,
    picks the most recently created (treat as newest version).
    """
    def _q(reg: str):
        return (
            db.query(EmissionFactor)
            .filter(EmissionFactor.region == reg, EmissionFactor.activity_type == activity_type)
            .order_by(EmissionFactor.created_at.desc())
            .first()
        )

    return _q(region) or _q("GLOBAL")


# --- effective tariff -----------------------------------------------------

def effective_tariff(db: Session) -> float:
    """Currency-per-kWh derived from utility bills (total cost / total kWh),
    falling back to the configured default tariff."""
    row = (
        db.query(func.sum(UtilityBill.cost), func.sum(UtilityBill.kwh))
        .filter(UtilityBill.cost.isnot(None))
        .first()
    )
    total_cost, total_kwh = row or (None, None)
    if total_cost and total_kwh and total_kwh > 0:
        return float(total_cost) / float(total_kwh)
    return settings.electricity_tariff


# --- emission computation -------------------------------------------------

def _source_by_id(db: Session) -> dict[int, EnergySource]:
    return {s.id: s for s in db.query(EnergySource).all()}


def recompute_emissions(db: Session) -> dict:
    """Regenerate all EmissionRecords from current UtilityBills + FuelLogs.

    Idempotent: clears bill/fuel-derived records and rebuilds them.
    """
    seed_factors_if_empty(db)  # guarantee reference data exists before computing
    db.query(EmissionRecord).filter(
        EmissionRecord.origin.in_(["utility_bill", "fuel_log"])
    ).delete(synchronize_session=False)

    sources = _source_by_id(db)
    n = 0

    # Scope 2 — grid electricity from utility bills
    for bill in db.query(UtilityBill).all():
        region = bill.region or settings.default_region
        factor = get_factor(db, region, "grid_electricity")
        if not factor:
            continue
        kgco2e = bill.kwh * factor.kgco2e_per_unit
        db.add(EmissionRecord(
            scope=factor.scope,
            source_type="grid",
            activity_type="grid_electricity",
            activity_amount=bill.kwh,
            activity_unit="kWh",
            factor_id=factor.id,
            kgco2e=kgco2e,
            cost=bill.cost,
            currency=bill.currency,
            period_start=bill.period_start,
            period_end=bill.period_end,
            data_quality=bill.data_quality or DataQuality.BILL,
            origin="utility_bill",
            origin_id=bill.id,
        ))
        n += 1

    # Scope 1 — fuel combustion from fuel logs (diesel gensets etc.)
    for log in db.query(FuelLog).all():
        region = log.region or settings.default_region
        factor = get_factor(db, region, log.fuel_type)
        if not factor:
            continue
        litres = log.litres
        quality = log.data_quality or DataQuality.BILL
        if litres is None and log.runtime_hours is not None:
            src = sources.get(log.source_id) if log.source_id else None
            lph = (src.genset_litres_per_hour if src and src.genset_litres_per_hour
                   else DEFAULT_GENSET_LITRES_PER_HOUR)
            litres = log.runtime_hours * lph
            quality = DataQuality.ESTIMATED  # derived from runtime
        if litres is None:
            continue
        kgco2e = litres * factor.kgco2e_per_unit
        db.add(EmissionRecord(
            scope=factor.scope,
            source_type="diesel_genset" if log.fuel_type == "diesel" else log.fuel_type,
            activity_type=log.fuel_type,
            activity_amount=litres,
            activity_unit=factor.unit,
            factor_id=factor.id,
            kgco2e=kgco2e,
            cost=log.cost,
            currency=log.currency,
            period_start=log.period_start,
            period_end=log.period_end,
            data_quality=quality,
            origin="fuel_log",
            origin_id=log.id,
        ))
        n += 1

    db.commit()
    return {"records": n}


# --- energy waste (the predictive-maintenance link) -----------------------

_PENALTY = {
    Severity.HIGH: settings.waste_penalty_high,
    Severity.MEDIUM: settings.waste_penalty_medium,
    Severity.MONITOR: settings.waste_penalty_monitor,
}
_SEV_RANK = {Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.MONITOR: 1}


def _machine_hours(db: Session, machine_id: int) -> float:
    """Observation span (hours) of a machine's sensor readings."""
    from app.models import SensorReading
    lo, hi = (
        db.query(func.min(SensorReading.ts), func.max(SensorReading.ts))
        .filter(SensorReading.machine_id == machine_id)
        .first()
    ) or (None, None)
    if not lo or not hi or hi <= lo:
        return 0.0
    return (hi - lo).total_seconds() / 3600.0


def estimate_machine_waste(db: Session, machine: Machine) -> dict | None:
    """Estimate energy/CO2/cost a degrading machine is wasting.

    Method: worst anomaly severity → efficiency penalty → applied to the machine's
    energy use over the observed window (rated_power_kw × hours). Requires
    ``rated_power_kw`` to be set. Returns None if it can't be estimated.
    """
    if not machine.rated_power_kw:
        return None
    # Worst severity: fetch the machine's distinct severities and rank in Python
    # (portable across SQLite/Postgres).
    sevs = [
        s for (s,) in db.query(Anomaly.severity)
        .filter(Anomaly.machine_id == machine.id)
        .distinct()
        .all()
    ]
    if not sevs:
        return None
    worst_sev = max(sevs, key=lambda s: _SEV_RANK.get(s, 0))
    penalty = _PENALTY.get(worst_sev, 0.0)
    if penalty <= 0:
        return None

    hours = _machine_hours(db, machine.id)
    if hours <= 0:
        return None

    energy_kwh = machine.rated_power_kw * hours
    wasted_kwh = energy_kwh * penalty

    region = settings.default_region
    factor = get_factor(db, region, "grid_electricity")
    co2 = wasted_kwh * (factor.kgco2e_per_unit if factor else 0.0)
    tariff = effective_tariff(db)
    cost = wasted_kwh * tariff
    return {
        "machine_id": machine.id,
        "machine": machine.name,
        "severity": worst_sev,
        "rated_power_kw": machine.rated_power_kw,
        "hours": round(hours, 1),
        "wasted_kwh": round(wasted_kwh, 1),
        "wasted_kgco2e": round(co2, 1),
        "saveable_cost": round(cost, 0),
        "currency": settings.default_currency,
    }


def fleet_waste(db: Session) -> list[dict]:
    out = []
    for m in db.query(Machine).all():
        w = estimate_machine_waste(db, m)
        if w:
            out.append(w)
    out.sort(key=lambda w: w["wasted_kgco2e"], reverse=True)
    return out


# --- summary --------------------------------------------------------------

def emissions_summary(db: Session) -> dict:
    """Aggregate inventory + waste + factor provenance for the dashboard/report."""
    records = db.query(EmissionRecord).all()

    by_scope: dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0}
    by_source: dict[str, float] = {}
    total_kwh = 0.0
    total_cost = 0.0
    currency = settings.default_currency
    for r in records:
        by_scope[r.scope] = by_scope.get(r.scope, 0.0) + r.kgco2e
        by_source[r.source_type] = by_source.get(r.source_type, 0.0) + r.kgco2e
        if r.activity_unit == "kWh":
            total_kwh += r.activity_amount
        if r.cost:
            total_cost += r.cost
            currency = r.currency or currency

    waste = fleet_waste(db)
    waste_kwh = sum(w["wasted_kwh"] for w in waste)
    waste_co2 = sum(w["wasted_kgco2e"] for w in waste)
    waste_cost = sum(w["saveable_cost"] for w in waste)

    total_co2 = sum(by_scope.values())

    factors = [
        {
            "region": f.region,
            "activity_type": f.activity_type,
            "scope": f.scope,
            "kgco2e_per_unit": f.kgco2e_per_unit,
            "unit": f.unit,
            "source": f.source,
        }
        for f in db.query(EmissionFactor).order_by(EmissionFactor.activity_type).all()
    ]

    return {
        "total_kgco2e": round(total_co2, 1),
        "total_tonnes_co2e": round(total_co2 / 1000.0, 2),
        "scope1_kgco2e": round(by_scope.get(1, 0.0), 1),
        "scope2_kgco2e": round(by_scope.get(2, 0.0), 1),
        "scope3_kgco2e": round(by_scope.get(3, 0.0), 1),
        "total_kwh": round(total_kwh, 1),
        "total_energy_cost": round(total_cost, 0),
        "currency": currency,
        "by_source": [{"source": k, "kgco2e": round(v, 1)} for k, v in sorted(
            by_source.items(), key=lambda kv: kv[1], reverse=True)],
        "record_count": len(records),
        "waste": {
            "wasted_kwh": round(waste_kwh, 1),
            "wasted_kgco2e": round(waste_co2, 1),
            "saveable_cost": round(waste_cost, 0),
            "currency": settings.default_currency,
            "machines": waste,
        },
        "factors": factors,
        "generated_at": datetime.utcnow().isoformat(),
    }
