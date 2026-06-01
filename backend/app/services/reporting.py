"""Regulatory report generator (Phase 8).

One engine, many templates. Each template shapes the SAME audited carbon data
(Phase 6) into a framework's structure, carrying methodology + emission-factor
provenance so the report is defensible to an auditor.

Frameworks:
  * ISSB  — IFRS S2 / GHG Protocol baseline (the neutral, reusable inventory)
  * CBAM  — EU Carbon Border Adjustment Mechanism (embedded emissions of goods)
  * BRSR  — India SEBI Business Responsibility & Sustainability Reporting (Principle 6)

These are decision-support drafts. Emission factors are labelled defaults that must
be replaced with the operator's official region/year factors, and the figures must
be validated (and, where required, externally assured) before filing.
"""
from __future__ import annotations

from datetime import datetime
from html import escape

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import EmissionFactor, EmissionRecord, Framework, RegulatoryReport
from app.services import carbon

KWH_TO_GJ = 0.0036  # 1 kWh = 0.0036 GJ


# --- period-scoped aggregation -------------------------------------------

def _records_in_period(db: Session, start: datetime, end: datetime) -> list[EmissionRecord]:
    """Emission records whose period overlaps [start, end]."""
    return (
        db.query(EmissionRecord)
        .filter(
            or_(
                EmissionRecord.period_start <= end,
                EmissionRecord.period_start.is_(None),
            ),
            or_(
                EmissionRecord.period_end >= start,
                EmissionRecord.period_end.is_(None),
            ),
        )
        .order_by(EmissionRecord.period_start.asc())
        .all()
    )


def _aggregate(records: list[EmissionRecord]) -> dict:
    by_scope = {1: 0.0, 2: 0.0, 3: 0.0}
    by_quality: dict[str, float] = {}
    kwh = 0.0
    fuel_litres = 0.0
    cost = 0.0
    currency = None
    for r in records:
        by_scope[r.scope] = by_scope.get(r.scope, 0.0) + r.kgco2e
        by_quality[r.data_quality] = by_quality.get(r.data_quality, 0.0) + r.kgco2e
        if r.activity_unit == "kWh":
            kwh += r.activity_amount
        if r.activity_unit == "litre":
            fuel_litres += r.activity_amount
        if r.cost:
            cost += r.cost
            currency = r.currency or currency
    total = sum(by_scope.values())
    return {
        "scope1_kgco2e": round(by_scope.get(1, 0.0), 1),
        "scope2_kgco2e": round(by_scope.get(2, 0.0), 1),
        "scope3_kgco2e": round(by_scope.get(3, 0.0), 1),
        "total_kgco2e": round(total, 1),
        "total_tonnes_co2e": round(total / 1000.0, 3),
        "electricity_kwh": round(kwh, 1),
        "energy_gj": round(kwh * KWH_TO_GJ, 2),
        "fuel_litres": round(fuel_litres, 1),
        "energy_cost": round(cost, 0),
        "currency": currency,
        "by_data_quality": {k: round(v, 1) for k, v in by_quality.items()},
        "record_count": len(records),
    }


def _factor_citations(db: Session, records: list[EmissionRecord]) -> list[dict]:
    """The distinct emission factors actually used — provenance for assurance."""
    ids = {r.factor_id for r in records if r.factor_id}
    if not ids:
        return []
    rows = db.query(EmissionFactor).filter(EmissionFactor.id.in_(ids)).all()
    return [
        {
            "region": f.region,
            "activity_type": f.activity_type,
            "scope": f.scope,
            "kgco2e_per_unit": f.kgco2e_per_unit,
            "unit": f.unit,
            "source": f.source,
            "version": f.version,
        }
        for f in rows
    ]


_DISCLAIMER = (
    "Decision-support draft. Emission factors are labelled defaults and must be replaced "
    "with the operator's official region- and year-specific factors. Figures must be "
    "validated and, where required (e.g. BRSR Core, CBAM verification), externally assured "
    "before filing. Not legal or accounting advice."
)


# --- template builders ----------------------------------------------------

def _issb_payload(agg: dict, citations: list[dict]) -> dict:
    return {
        "standard": "IFRS S2 / GHG Protocol",
        "sections": [
            {"title": "Gross Scope 1 emissions", "value": agg["scope1_kgco2e"], "unit": "kgCO2e"},
            {"title": "Gross Scope 2 emissions (location-based)", "value": agg["scope2_kgco2e"], "unit": "kgCO2e"},
            {"title": "Gross Scope 3 emissions", "value": agg["scope3_kgco2e"], "unit": "kgCO2e",
             "note": "Not yet inventoried — value-chain data required (later phase)."},
            {"title": "Total gross emissions", "value": agg["total_tonnes_co2e"], "unit": "tCO2e"},
            {"title": "Energy consumption", "value": agg["energy_gj"], "unit": "GJ"},
        ],
        "methodology": (
            "Scope 1 from fuel combustion (diesel gensets); Scope 2 from purchased grid "
            "electricity. Activity data × region-specific emission factors per the GHG "
            "Protocol Corporate Standard. Location-based method for Scope 2."
        ),
    }


def _cbam_payload(agg: dict, citations: list[dict], production_tonnes: float | None) -> dict:
    direct = agg["scope1_kgco2e"]            # combustion at the installation
    indirect = agg["scope2_kgco2e"]          # purchased electricity
    total = direct + indirect
    section = [
        {"title": "Direct embedded emissions (Scope 1)", "value": round(direct, 1), "unit": "kgCO2e"},
        {"title": "Indirect embedded emissions (electricity)", "value": round(indirect, 1), "unit": "kgCO2e"},
        {"title": "Total embedded emissions", "value": round(total, 1), "unit": "kgCO2e"},
    ]
    intensity = None
    if production_tonnes and production_tonnes > 0:
        intensity = round(total / production_tonnes, 3)
        section.append({
            "title": "Specific embedded emissions (intensity)",
            "value": intensity, "unit": "kgCO2e / tonne product",
            "note": f"Total embedded emissions ÷ {production_tonnes} t production.",
        })
    return {
        "standard": "EU CBAM — installation emissions data",
        "production_tonnes": production_tonnes,
        "specific_embedded_emissions": intensity,
        "sections": section,
        "methodology": (
            "Embedded emissions = direct combustion (Scope 1) + electricity (indirect) at "
            "the installation over the reporting period. Specific embedded emissions = total "
            "÷ production output. Simplified vs. the full CBAM methodology (no precursors, "
            "carbon price, or installation-level monitoring plan) — for internal preparation."
        ),
    }


def _brsr_payload(agg: dict, citations: list[dict]) -> dict:
    return {
        "standard": "SEBI BRSR — Principle 6 (Environment)",
        "sections": [
            {"title": "Total electricity consumption", "value": agg["energy_gj"], "unit": "GJ",
             "note": f"{agg['electricity_kwh']} kWh"},
            {"title": "Total Scope 1 emissions", "value": agg["scope1_kgco2e"], "unit": "kgCO2e (metric tonnes CO2e ÷1000)"},
            {"title": "Total Scope 2 emissions", "value": agg["scope2_kgco2e"], "unit": "kgCO2e"},
            {"title": "Total Scope 1 + 2 emissions", "value": round(agg["scope1_kgco2e"] + agg["scope2_kgco2e"], 1), "unit": "kgCO2e"},
        ],
        "methodology": (
            "Energy and emissions per BRSR Principle 6 essential indicators. Scope 1 from "
            "diesel/fuel, Scope 2 from grid electricity using the applicable Indian grid "
            "emission factor. BRSR Core indicators require reasonable assurance."
        ),
    }


_TITLES = {
    Framework.ISSB: "ISSB / GHG Protocol Climate Disclosure",
    Framework.CBAM: "EU CBAM Embedded-Emissions Report",
    Framework.BRSR: "BRSR Principle 6 — Environment Disclosure",
}


def generate(
    db: Session,
    framework: str,
    period_start: datetime,
    period_end: datetime,
    region: str = "GLOBAL",
    production_tonnes: float | None = None,
) -> RegulatoryReport:
    """Build and persist a regulatory report for the period."""
    carbon.seed_factors_if_empty(db)
    carbon.recompute_emissions(db)  # ensure inventory reflects current inputs

    records = _records_in_period(db, period_start, period_end)
    agg = _aggregate(records)
    citations = _factor_citations(db, records)

    if framework == Framework.CBAM:
        body = _cbam_payload(agg, citations, production_tonnes)
    elif framework == Framework.BRSR:
        body = _brsr_payload(agg, citations)
    else:
        framework = Framework.ISSB
        body = _issb_payload(agg, citations)

    payload = {
        "framework": framework,
        "region": region,
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
        "summary": agg,
        **body,
        "emission_factors": citations,
        "data_quality": agg["by_data_quality"],
        "disclaimer": _DISCLAIMER,
        "generated_at": datetime.utcnow().isoformat(),
    }

    report = RegulatoryReport(
        framework=framework,
        title=_TITLES.get(framework, framework),
        region=region,
        period_start=period_start,
        period_end=period_end,
        payload=payload,
        status="draft",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# --- rendering ------------------------------------------------------------

def render_html(report: RegulatoryReport) -> str:
    """A clean, self-contained printable report (browser → PDF). No deps."""
    p = report.payload or {}
    period = p.get("period", {})
    rows = "".join(
        f"<tr><td>{escape(str(s.get('title','')))}</td>"
        f"<td class='num'>{escape(str(s.get('value','')))}</td>"
        f"<td class='unit'>{escape(str(s.get('unit','')))}</td>"
        f"<td class='note'>{escape(str(s.get('note','') or ''))}</td></tr>"
        for s in p.get("sections", [])
    )
    factors = "".join(
        f"<li>{escape(f['region'])} · {escape(f['activity_type'])}: "
        f"{f['kgco2e_per_unit']} kgCO₂e/{escape(f['unit'])} "
        f"<span class='src'>— {escape(f['source'])}</span></li>"
        for f in p.get("emission_factors", [])
    ) or "<li>No emission factors recorded.</li>"
    dq = "".join(
        f"<li>{escape(k)}: {v} kgCO₂e</li>" for k, v in (p.get("data_quality") or {}).items()
    ) or "<li>—</li>"

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{escape(report.title)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; color: #1a1a1a; max-width: 820px; margin: 40px auto; padding: 0 24px; }}
  h1 {{ font-size: 22px; margin-bottom: 2px; }}
  .meta {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
  .badge {{ display:inline-block; background:#111; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; letter-spacing:.08em; text-transform:uppercase; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e3e3e3; font-size: 14px; }}
  th {{ font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #888; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }}
  td.unit, td.note {{ color: #666; font-size: 12px; }}
  h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: #555; margin-top: 28px; }}
  .method, .disc {{ font-size: 13px; color: #333; line-height: 1.5; }}
  .disc {{ background:#fbf7e9; border:1px solid #ece0b8; padding:12px; border-radius:6px; color:#5b4a16; }}
  ul {{ font-size: 13px; color:#333; }} .src {{ color:#888; }}
  footer {{ margin-top:32px; color:#999; font-size:11px; border-top:1px solid #e3e3e3; padding-top:10px; }}
</style></head><body>
  <span class="badge">{escape(report.framework)}</span>
  <h1>{escape(report.title)}</h1>
  <div class="meta">
    Region {escape(report.region)} ·
    Period {escape(period.get('start','')[:10])} → {escape(period.get('end','')[:10])} ·
    Standard: {escape(str(p.get('standard','')))}
  </div>

  <table>
    <thead><tr><th>Indicator</th><th class="num">Value</th><th>Unit</th><th>Note</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Methodology</h2>
  <p class="method">{escape(str(p.get('methodology','')))}</p>

  <h2>Emission factors used (provenance)</h2>
  <ul>{factors}</ul>

  <h2>Data quality</h2>
  <ul>{dq}</ul>

  <h2>Disclaimer</h2>
  <p class="disc">{escape(str(p.get('disclaimer','')))}</p>

  <footer>Generated {escape(str(p.get('generated_at','')))} · Predictive Maintenance Copilot — Carbon &amp; Compliance</footer>
</body></html>"""
