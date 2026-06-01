"""Pydantic request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


# --- Auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    org_id: int | None = None
    role: str = "operator"
    created_at: datetime


# --- Phase 7: organizations / sites / roles ---
class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    country: str | None = None
    created_at: datetime


class SiteCreate(BaseModel):
    name: str
    location: str | None = None
    region: str = "GLOBAL"


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    name: str
    location: str | None = None
    region: str
    created_at: datetime


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    role: str


class RoleUpdate(BaseModel):
    role: str  # owner | manager | operator | auditor


class MachineSiteUpdate(BaseModel):
    site_id: int | None = None


# --- Phase 9: sensor ingestion (gateway / edge agent target) ---
class IngestReading(BaseModel):
    machine: str
    ts: datetime
    temperature: float | None = None
    pressure: float | None = None
    vibration: float | None = None
    rpm: float | None = None
    power_kw: float | None = None


class IngestBatch(BaseModel):
    readings: list[IngestReading]


# --- Phase 10: audit ledger ---
class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    seq: int
    event_type: str
    entity: str | None = None
    entity_id: int | None = None
    summary: str
    actor: str | None = None
    hash: str
    prev_hash: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Datasets / upload ---
class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    uploaded_at: datetime
    row_count: int
    status: str
    error: str | None = None


# --- Machines / fleet ---
class MachineHealth(BaseModel):
    id: int
    name: str
    machine_type: str | None = None
    location: str | None = None
    health: str  # green | yellow | red
    anomaly_count: int
    high_count: int
    medium_count: int
    monitor_count: int
    trending_count: int
    last_reading: datetime | None = None
    max_z: float = 0.0
    latest: dict[str, float | None] = {}
    spark_param: str = "temperature"
    spark: list[float] = []


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    parameter: str
    ts: datetime
    value: float
    z_score: float
    severity: str
    is_trending: bool
    trend_slope: float | None = None


class ReadingPoint(BaseModel):
    ts: datetime
    temperature: float | None = None
    pressure: float | None = None
    vibration: float | None = None
    rpm: float | None = None
    temperature_roll_avg: float | None = None
    pressure_roll_avg: float | None = None
    vibration_roll_avg: float | None = None
    rpm_roll_avg: float | None = None


class MachineDetail(BaseModel):
    machine: MachineHealth
    readings: list[ReadingPoint]
    anomalies: list[AnomalyOut]


# --- Recommendations / chat ---
class RecommendRequest(BaseModel):
    machine_id: int | None = None
    question: str
    session_id: str | None = None
    use_manuals: bool = True


class Citation(BaseModel):
    source: str
    snippet: str
    page: int | None = None
    section: str | None = None
    score: float | None = None


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_id: int | None = None
    session_id: str | None = None
    question: str
    verdict: str
    explanation: str
    citations: list | None = None
    created_at: datetime


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: str
    role: str
    content: str
    created_at: datetime


# --- Documents ---
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    uploaded_at: datetime
    status: str
    chunk_count: int
    error: str | None = None


# --- Maintenance log ---
class MaintenanceLogCreate(BaseModel):
    recommendation_id: int | None = None
    machine_id: int | None = None
    notes: str | None = None


class MaintenanceLogUpdate(BaseModel):
    actioned: bool | None = None
    notes: str | None = None


class RerunRequest(BaseModel):
    method: str = "zscore"
    threshold: float = 3.0
    window: int = 10


class DetectionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mlflow_run_id: str | None = None
    params: dict | None = None
    metrics: dict | None = None
    created_at: datetime


class ForecastOut(BaseModel):
    parameter: str
    unit: str
    current: float
    limit: float
    slope_per_day: float
    eta_days: float | None = None
    status: str  # exceeded | approaching | stable


class MaintenanceLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recommendation_id: int | None = None
    machine_id: int | None = None
    actioned: bool
    notes: str | None = None
    actioned_at: datetime | None = None
    created_at: datetime


# --- Phase 6: energy & carbon ---
class EmissionFactorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    region: str
    activity_type: str
    scope: int
    kgco2e_per_unit: float
    unit: str
    source: str
    version: str | None = None


class EnergySourceCreate(BaseModel):
    name: str
    source_type: str  # grid | diesel_genset | solar | natural_gas
    region: str = "GLOBAL"
    genset_litres_per_hour: float | None = None


class EnergySourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    source_type: str
    region: str
    genset_litres_per_hour: float | None = None
    created_at: datetime


class UtilityBillCreate(BaseModel):
    source_id: int | None = None
    period_start: datetime
    period_end: datetime
    kwh: float
    cost: float | None = None
    currency: str = "INR"
    region: str = "GLOBAL"


class UtilityBillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: int | None = None
    period_start: datetime
    period_end: datetime
    kwh: float
    cost: float | None = None
    currency: str
    region: str
    data_quality: str
    created_at: datetime


class FuelLogCreate(BaseModel):
    source_id: int | None = None
    period_start: datetime
    period_end: datetime
    fuel_type: str = "diesel"
    litres: float | None = None
    runtime_hours: float | None = None
    cost: float | None = None
    currency: str = "INR"
    region: str = "GLOBAL"


class FuelLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: int | None = None
    period_start: datetime
    period_end: datetime
    fuel_type: str
    litres: float | None = None
    runtime_hours: float | None = None
    cost: float | None = None
    currency: str
    region: str
    data_quality: str
    created_at: datetime


class MachineRatedPowerUpdate(BaseModel):
    rated_power_kw: float | None = None


# --- Phase 8: regulatory reports ---
class ReportGenerateRequest(BaseModel):
    framework: str  # ISSB | CBAM | BRSR
    period_start: datetime
    period_end: datetime
    region: str = "GLOBAL"
    production_tonnes: float | None = None  # CBAM intensity


class RegulatoryReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    framework: str
    title: str
    region: str
    period_start: datetime
    period_end: datetime
    status: str
    created_at: datetime


class RegulatoryReportDetail(RegulatoryReportOut):
    payload: dict | None = None
