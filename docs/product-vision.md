# Product Vision — Carbon & Compliance Copilot for Factories

> From a predictive-maintenance demo to a **sellable, end-to-end energy + carbon +
> regulatory-reporting platform** for factories in India, Africa, and South-East Asia
> (Malaysia, Thailand, Indonesia, Vietnam, …).

This document is the north star. It captures **why** the product exists, **who** buys it,
the **regulatory landscape** it serves, the **architecture** that makes it work in these
markets, and the **phased roadmap**. Companion technical detail for the carbon engine lives
in [`esg.md`](esg.md).

---

## 1. The thesis (why anyone pays)

> **The factory owner pays to cut the energy bill. The government makes the carbon
> report mandatory. We sell one product that does both.**

- Predictive maintenance catches **energy waste** (a degrading pump/motor burns more kWh for
  the same work) → directly cuts the electricity + diesel bill. This is the *want* — it has a
  hard ROI the plant manager understands.
- The **same** sensor/energy data feeds a **verified carbon-accounting engine** → which
  auto-generates the **specific regulatory report** each jurisdiction now demands, with an
  audit trail. This is the *must* — increasingly it is the law and, for exporters, a condition
  of keeping their customers.

One platform, two reasons to buy, one of which is becoming non-optional. That is the wedge.

---

## 2. Who buys, and why now

| Buyer | Primary pain | What we sell them |
|---|---|---|
| SME factory owner (India / Africa / SE Asia) | High & rising energy bill; diesel costs | Maintenance + energy-waste savings (fast ROI) |
| Exporter to the EU | EU **CBAM** forces them to declare product carbon or lose the buyer | Embedded-carbon calc + CBAM declaration |
| Large listed firm (India) | **BRSR** (+ assured BRSR Core) is mandatory | Auto-drafted, audit-ready sustainability report |
| Plant in a carbon-tax country (e.g. South Africa) | Carbon tax filing is due and real money | Scope 1/2 calc + tax-ready filing |
| Group sustainability / CSO | Fragmented data, manual spreadsheets, audit risk | One source of truth, traceable to source docs |

**Why now:** EU CBAM enters its definitive regime in 2026; India's BRSR Core requires
third-party assurance; Malaysia/Thailand are adopting ISSB; South Africa already taxes carbon.
The reporting burden is arriving in these exact markets, and tooling built *for* them barely
exists.

---

## 3. Regulatory landscape (target all, phased)

The key architectural insight: **almost every framework below sits on top of the GHG Protocol
(Scope 1/2/3) and is converging on ISSB (IFRS S1/S2).** So we build **one** carbon engine to
GHG Protocol + ISSB, and each country's report becomes a **different export template** over the
same verified data.

| Framework | Region | What it requires | Phase |
|---|---|---|---|
| **GHG Protocol + ISSB S2** | Global baseline | Scope 1/2/3 inventory, climate disclosure | core |
| **EU CBAM** | Exporters → EU | Embedded carbon of goods (steel, aluminium, cement, fertiliser, …) | 8a |
| **India BRSR / BRSR Core** | India (SEBI) | Sustainability disclosure; BRSR Core needs *assurance* | 8b |
| **South Africa carbon tax** | South Africa | Scope 1 emissions → tax filing | 8c |
| **Malaysia NSRF / Bursa, Thailand SET ESG** | SE Asia | ISSB-aligned disclosure | 8d |

> Disclaimer: this is product-design orientation, not legal advice. Final templates must be
> validated against the then-current official guidance and, where required (e.g. BRSR Core,
> CBAM), by an accredited assurer.

---

## 4. Ground truth — designing for *these* markets

A product that works in the EU/US but ignores local reality will not sell here. Non-negotiable
design constraints:

1. **Diesel gensets are everywhere.** Unreliable grids mean factories run diesel generators
   constantly — a major **Scope 1** source. Capturing genset runtime / fuel logs is mandatory,
   or the carbon numbers are simply wrong.
2. **Intermittent connectivity.** Offline-first capture with buffering and later sync is
   required, not a nice-to-have → this is the core reason for an **edge agent**.
3. **Most factories have no sensors.** We need **three input paths** (see §5). Many pilots will
   start with nothing but a monthly electricity bill and diesel purchase receipts — and we must
   turn *that* into a credible report.
4. **Multi-language.** Hindi + Indian regional languages, Bahasa Malaysia/Indonesia, Thai,
   French (Francophone Africa), Swahili. i18n from the start.
5. **Tight budgets + data sovereignty.** Tiered pricing, runs on modest hardware, **on-prem /
   self-hosted option**; India **DPDP Act 2023** and similar laws favour local data residency.
6. **Multi-tenant.** Selling to many factories means org/site isolation and real roles
   (operator, plant manager, auditor, regulator read-only).

---

## 5. The three data-input paths (and where Go / Rust come in)

The product must accept data at whatever maturity the factory is at:

| Path | What it is | Language | When |
|---|---|---|---|
| **A. Utility bills + manual entry** | Upload/keying of electricity bills, diesel receipts, runtime logs | **Python** (existing stack) | Phase 6–7 — lowest barrier, first paying pilots |
| **B. Real sensors / meters** | API ingestion of streaming meter/sensor data (extends today's CSV flow) | **Python** now; **Go** ingestion gateway at scale | Phase 7, gateway in Phase 9 |
| **C. Edge agent / retrofit sensors** | On-floor software that reads sensors, buffers offline, syncs when online | **Rust** | Phase 9 |

**This is the honest answer to "will Go and Rust be needed?": yes, but only for paths B-at-scale
and C.**

- **Rust — the edge agent.** Runs on a cheap industrial PC / Raspberry Pi on the factory floor.
  Must be tiny, reliable, run for months unattended, and buffer data through internet outages.
  Rust is the right tool: small footprint, memory-safe, no GC pauses, excellent for long-running
  embedded/edge software.
- **Go — the ingestion gateway.** *Only* once many factories stream sensor data concurrently. A
  small Go service in front of Python handles thousands of simultaneous connections cleanly
  (Go's concurrency model fits this exactly), then hands normalized data to the Python core.
- **Everything else stays Python.** The carbon engine, ML/RAG, report generation, API, and UI
  remain Python/React. We go polyglot **by measured necessity, never by rewrite.** The Python
  core is never replaced — Go and Rust are satellites around it.

---

## 6. Architecture deltas from today

Current system (single-tenant PdM): React + FastAPI + PostgreSQL + ChromaDB + MLflow + Celery.
What the product adds:

- **Multi-tenancy:** new `Organization` and `Site` above `Machine`; tenant-scoped queries;
  roles (operator / manager / auditor / regulator-view).
- **Energy & emissions model:** `EnergySource` (grid / diesel genset / solar), `FuelLog`,
  `UtilityBill`, versioned regional `EmissionFactor`, computed `EmissionRecord` (Scope 1/2/3).
  Detail in [`esg.md`](esg.md).
- **Regulatory report generator:** pluggable templates (CBAM, BRSR, ISSB S2, SA carbon tax)
  rendering PDF / structured bundles, each line traceable to its source data + method. Reuses
  the existing RAG citation discipline so reports are *defensible to an auditor*.
- **Ingestion gateway (Go)** and **edge agent (Rust)** as separate services (§5).
- **i18n** across the frontend; **on-prem packaging** (Docker Compose already exists — extend
  to an air-gapped profile).
- **Assurance/audit mode:** append-only emission ledger + read-only external-auditor access
  (BRSR Core / CBAM verification need this).

---

## 7. Phased roadmap

Each phase is independently demoable and, from Phase 6 on, independently sellable.

- **Phase 6 — Carbon core (Python).** Energy → Scope 1/2 → CO₂. Diesel-genset Scope 1.
  Versioned emission factors. Utility-bill + manual input path (A). Dashboard tiles +
  `/api/export/sustainability.csv`. *Foundation for everything below.*
- **Phase 7 — Multi-tenant + roles + richer input.** `Organization`/`Site`, RBAC, sensor
  API ingestion (path B in Python). Makes it deployable to many real factories.
- **Phase 8 — Regulatory report generator.** Shared engine + templates, shipped in order:
  **8a CBAM → 8b BRSR → 8c South Africa carbon tax → 8d Malaysia/Thailand ISSB.**
- **Phase 9 — Edge & scale.** Rust edge agent + offline sync (path C); Go ingestion gateway
  (path B at scale); i18n; on-prem/air-gapped packaging.
- **Phase 10 — Assurance & audit.** Append-only ledger, external-auditor read-only access,
  verification workflow for BRSR Core / CBAM.

---

## 8. What stays the same (your existing strengths carry over)

- **RAG with citations** → becomes the engine for *defensible, source-cited reports*.
- **MLflow tracking** → audit trail for every detection/calculation run.
- **ETL engine interface (pandas ↔ Spark)** → already scales the data layer.
- **Celery / Redis** → already there for scheduled monthly/quarterly report generation.
- **Maintenance log (`actioned`)** → becomes the **avoided-impact / savings ledger**.

The product is an *evolution* of what exists, not a rewrite — which is exactly why it's
buildable on a realistic timeline.
