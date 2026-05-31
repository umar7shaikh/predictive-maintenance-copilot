"""Linear trend forecasting: project when a rising parameter crosses its limit.

Limits default to the thresholds in the sample HP-series manual; in production
these would come from per-equipment manual metadata.
"""
import numpy as np

# (limit, unit) per parameter. None = no meaningful upper limit (skip).
DEFAULT_LIMITS = {
    "temperature": (75.0, "°C"),
    "vibration": (4.0, "mm/s"),
    "pressure": (165.0, "bar"),
    "rpm": (None, "rpm"),
}

HORIZON_DAYS = 120  # don't bother flagging crossings beyond this


def forecast_machine(readings: list) -> list[dict]:
    """readings: ORM SensorReading rows (any order). Returns per-parameter forecast."""
    rows = sorted(readings, key=lambda r: r.ts)
    if len(rows) < 5:
        return []

    t0 = rows[0].ts
    hours = np.array([(r.ts - t0).total_seconds() / 3600.0 for r in rows])

    out: list[dict] = []
    for param, (limit, unit) in DEFAULT_LIMITS.items():
        if limit is None:
            continue
        vals = np.array([getattr(r, param) for r in rows], dtype="float64")
        mask = ~np.isnan(vals)
        if mask.sum() < 5:
            continue
        x, y = hours[mask], vals[mask]
        slope, intercept = np.polyfit(x, y, 1)  # per hour
        current = float(y[-3:].mean())  # smooth the latest reading a touch
        slope_per_day = slope * 24.0

        eta_days = None
        if current >= limit:
            status = "exceeded"
        elif slope > 0:
            eta_days = float((limit - current) / slope_per_day)
            status = "approaching" if eta_days <= HORIZON_DAYS else "stable"
        else:
            status = "stable"

        out.append(
            {
                "parameter": param,
                "unit": unit,
                "current": round(current, 2),
                "limit": limit,
                "slope_per_day": round(slope_per_day, 4),
                "eta_days": round(eta_days, 1) if eta_days is not None else None,
                "status": status,
            }
        )
    # Surface the most urgent first.
    order = {"exceeded": 0, "approaching": 1, "stable": 2}
    out.sort(key=lambda f: (order[f["status"]], f["eta_days"] if f["eta_days"] is not None else 1e9))
    return out
