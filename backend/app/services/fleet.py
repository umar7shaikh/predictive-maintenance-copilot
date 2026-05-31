"""Fleet health computation and anomaly-summary text for the LLM."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Anomaly, Machine, SensorReading, Severity


def _health_from_counts(high: int, medium: int, monitor: int) -> str:
    if high > 0:
        return "red"
    if medium > 0:
        return "yellow"
    if monitor > 0:
        return "yellow"
    return "green"


def machine_health(db: Session, machine: Machine) -> dict:
    counts = (
        db.query(Anomaly.severity, func.count(Anomaly.id))
        .filter(Anomaly.machine_id == machine.id)
        .group_by(Anomaly.severity)
        .all()
    )
    c = {Severity.HIGH: 0, Severity.MEDIUM: 0, Severity.MONITOR: 0}
    for sev, n in counts:
        c[sev] = n
    trending = (
        db.query(func.count(Anomaly.id))
        .filter(Anomaly.machine_id == machine.id, Anomaly.is_trending.is_(True))
        .scalar()
    ) or 0
    # Most recent reading (for the monospace readouts on the fleet cards).
    latest_row = (
        db.query(SensorReading)
        .filter(SensorReading.machine_id == machine.id)
        .order_by(SensorReading.ts.desc())
        .first()
    )
    last_reading = latest_row.ts if latest_row else None
    latest = (
        {
            "temperature": latest_row.temperature,
            "pressure": latest_row.pressure,
            "vibration": latest_row.vibration,
            "rpm": latest_row.rpm,
        }
        if latest_row
        else {}
    )

    # Peak severity (largest |z|) and which parameter drives it -> sparkline metric.
    top = (
        db.query(Anomaly)
        .filter(Anomaly.machine_id == machine.id)
        .order_by(func.abs(Anomaly.z_score).desc())
        .first()
    )
    max_z = abs(top.z_score) if top else 0.0
    spark_param = top.parameter if top else "temperature"

    # Recent series of the driving parameter for an inline sparkline (oldest->newest).
    recent = (
        db.query(getattr(SensorReading, spark_param))
        .filter(SensorReading.machine_id == machine.id)
        .order_by(SensorReading.ts.desc())
        .limit(48)
        .all()
    )
    spark = [float(v[0]) for v in reversed(recent) if v[0] is not None]

    total = c[Severity.HIGH] + c[Severity.MEDIUM] + c[Severity.MONITOR]
    return {
        "id": machine.id,
        "name": machine.name,
        "machine_type": machine.machine_type,
        "location": machine.location,
        "health": _health_from_counts(c[Severity.HIGH], c[Severity.MEDIUM], c[Severity.MONITOR]),
        "anomaly_count": total,
        "high_count": c[Severity.HIGH],
        "medium_count": c[Severity.MEDIUM],
        "monitor_count": c[Severity.MONITOR],
        "trending_count": trending,
        "last_reading": last_reading,
        "max_z": round(max_z, 2),
        "latest": latest,
        "spark_param": spark_param,
        "spark": spark,
    }


def build_anomaly_summary(db: Session, machine_id: int | None = None) -> str:
    """Human-readable anomaly digest fed to the LLM."""
    q = db.query(Anomaly)
    if machine_id is not None:
        q = q.filter(Anomaly.machine_id == machine_id)

    anomalies = q.order_by(Anomaly.z_score.desc()).limit(40).all()
    if not anomalies:
        return "No anomalies detected in the analyzed sensor data."

    name_by_id = {m.id: m.name for m in db.query(Machine).all()}
    lines = []
    for a in anomalies:
        trend = " (worsening trend)" if a.is_trending else ""
        lines.append(
            f"- {name_by_id.get(a.machine_id, a.machine_id)}: {a.parameter} = "
            f"{a.value:.2f} at {a.ts:%Y-%m-%d %H:%M} | severity {a.severity}, "
            f"z={a.z_score:.2f}{trend}"
        )
    return "\n".join(lines)
