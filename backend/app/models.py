"""SQLAlchemy ORM models for the Predictive Maintenance Copilot."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# --- status / verdict constants (stored as plain strings) ---
class DatasetStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    MONITOR = "MONITOR"


class Verdict:
    URGENT_SERVICE = "URGENT_SERVICE"
    SCHEDULE_SERVICE = "SCHEDULE_SERVICE"
    MONITOR = "MONITOR"
    SAFE = "SAFE"


class Scope:
    """GHG Protocol emission scopes."""

    SCOPE_1 = 1  # direct (e.g. diesel genset combustion)
    SCOPE_2 = 2  # purchased electricity / heat
    SCOPE_3 = 3  # value chain (embedded carbon — CBAM, later phases)


class SourceType:
    """Where a site's energy comes from."""

    GRID = "grid"
    DIESEL_GENSET = "diesel_genset"
    SOLAR = "solar"
    NATURAL_GAS = "natural_gas"


class DataQuality:
    """How trustworthy an activity-data input is — auditors care about this."""

    MEASURED = "measured"      # from a calibrated meter
    BILL = "bill"              # from a utility bill / invoice
    ESTIMATED = "estimated"    # derived (e.g. runtime × rated consumption)


class Role:
    """User roles, ranked. Higher rank ⊇ lower-rank write permissions.
    Auditor is read-only regardless of rank (handled in the dependency)."""

    OWNER = "owner"        # rank 3 — full control of the org
    MANAGER = "manager"    # rank 2 — manage data, generate reports
    OPERATOR = "operator"  # rank 1 — enter readings / energy data
    AUDITOR = "auditor"    # rank 1, read-only — external assurance access

    RANK = {OWNER: 3, MANAGER: 2, OPERATOR: 1, AUDITOR: 1}
    READ_ONLY = {AUDITOR}


class Organization(Base):
    """Tenant — the company that owns sites, machines, and data."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)  # default region for factors
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Site(Base):
    """A physical plant within an organization."""

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str] = mapped_column(String(32), default="GLOBAL", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default=Role.OPERATOR, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    machine_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True)
    # Nameplate power draw — used to estimate energy use and waste when no power meter exists.
    rated_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    readings: Mapped[list["SensorReading"]] = relationship(back_populates="machine")
    anomalies: Mapped[list["Anomaly"]] = relationship(back_populates="machine")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=DatasetStatus.PENDING)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), index=True, nullable=False)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)

    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    vibration: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Optional metered power draw (kW). Feeds Scope 2 energy directly when present.
    power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)

    temperature_roll_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_roll_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    vibration_roll_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpm_roll_avg: Mapped[float | None] = mapped_column(Float, nullable=True)

    temperature_roc: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_roc: Mapped[float | None] = mapped_column(Float, nullable=True)
    vibration_roc: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpm_roc: Mapped[float | None] = mapped_column(Float, nullable=True)

    machine: Mapped["Machine"] = relationship(back_populates="readings")


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), index=True, nullable=False)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True, nullable=False)
    parameter: Mapped[str] = mapped_column(String(32), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    is_trending: Mapped[bool] = mapped_column(Boolean, default=False)
    trend_slope: Mapped[float | None] = mapped_column(Float, nullable=True)

    machine: Mapped["Machine"] = relationship(back_populates="anomalies")


class EtlRun(Base):
    __tablename__ = "etl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default=DatasetStatus.PENDING)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    machine_id: Mapped[int | None] = mapped_column(ForeignKey("machines.id"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendations.id"), nullable=True
    )
    machine_id: Mapped[int | None] = mapped_column(ForeignKey("machines.id"), nullable=True)
    actioned: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --- Phase 6: energy & carbon ---------------------------------------------


class EmissionFactor(Base):
    """Versioned reference data: kgCO2e per unit of activity, by region.

    Never hardcode factors in logic — they change yearly and vary by region.
    Each row records its source and validity window so every emission number
    computed from it is auditable.
    """

    __tablename__ = "emission_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # ISO-ish, e.g. IN, ZA, MY, TH, GLOBAL
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # grid_electricity | diesel | natural_gas | lpg
    scope: Mapped[int] = mapped_column(Integer, nullable=False)
    kgco2e_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)  # kWh | litre | m3 | kg
    source: Mapped[str] = mapped_column(String(255), nullable=False)  # provenance, e.g. "CEA CO2 Baseline DB v19"
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EnergySource(Base):
    """An energy source at the plant: grid, diesel genset, solar, gas."""

    __tablename__ = "energy_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # SourceType.*
    region: Mapped[str] = mapped_column(String(32), default="GLOBAL", nullable=False)
    # For diesel gensets: rated fuel burn used to estimate litres from runtime hours.
    genset_litres_per_hour: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UtilityBill(Base):
    """A grid-electricity (or other purchased-energy) bill for a billing period.

    The lowest-barrier input path: a factory with no sensors can still report by
    keying in its monthly electricity bill.
    """

    __tablename__ = "utility_bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("energy_sources.id"), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    kwh: Mapped[float] = mapped_column(Float, nullable=False)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="GLOBAL", nullable=False)
    data_quality: Mapped[str] = mapped_column(String(16), default=DataQuality.BILL, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FuelLog(Base):
    """Diesel / fuel consumed by a Scope-1 source over a period.

    Either litres (measured) or runtime hours (estimated via genset_litres_per_hour).
    """

    __tablename__ = "fuel_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("energy_sources.id"), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(32), default="diesel", nullable=False)
    litres: Mapped[float | None] = mapped_column(Float, nullable=True)
    runtime_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="GLOBAL", nullable=False)
    data_quality: Mapped[str] = mapped_column(String(16), default=DataQuality.BILL, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EmissionRecord(Base):
    """A computed emission line — fully traceable to its activity data + factor.

    Mirrors the Anomaly pattern: one row per computed result, regenerated when
    inputs change.
    """

    __tablename__ = "emission_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_amount: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. kWh or litres
    activity_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    factor_id: Mapped[int | None] = mapped_column(ForeignKey("emission_factors.id"), nullable=True)
    kgco2e: Mapped[float] = mapped_column(Float, nullable=False)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_quality: Mapped[str] = mapped_column(String(16), default=DataQuality.ESTIMATED, nullable=False)
    origin: Mapped[str | None] = mapped_column(String(32), nullable=True)  # utility_bill | fuel_log | meter
    origin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Framework:
    """Supported regulatory report templates."""

    ISSB = "ISSB"      # IFRS S2 / GHG Protocol baseline
    CBAM = "CBAM"      # EU Carbon Border Adjustment Mechanism
    BRSR = "BRSR"      # India SEBI Business Responsibility & Sustainability Reporting


class RegulatoryReport(Base):
    """A generated regulatory/disclosure report over a period.

    The ``payload`` holds the fully-structured, framework-specific figures plus the
    methodology and emission-factor provenance used to produce them — so the report
    is defensible to an auditor.
    """

    __tablename__ = "regulatory_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    framework: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="GLOBAL", nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    """Append-only, hash-chained audit ledger (Phase 10).

    Each event hashes its own content together with the previous event's hash,
    forming a tamper-evident chain: altering or deleting any past event breaks
    verification. This is the audit trail BRSR Core / CBAM assurance require.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)  # report.generate, emissions.recompute, ...
    entity: Mapped[str | None] = mapped_column(String(48), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AvoidedImpact(Base):
    """Decision-support estimate of energy/CO2/downtime saved by acting on a
    recommendation. Presented as avoided impact — never booked against the
    Scope 1/2 inventory.
    """

    __tablename__ = "avoided_impacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[int | None] = mapped_column(ForeignKey("machines.id"), nullable=True)
    maintenance_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("maintenance_logs.id"), nullable=True
    )
    wasted_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    avoided_kgco2e: Mapped[float] = mapped_column(Float, default=0.0)
    saveable_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
