# ESG / Carbon Engine — Technical Design

> The data model and calculation logic that turns factory energy use into a **verified,
> auditable carbon inventory** and feeds the regulatory report generator. Strategy and
> market context live in [`product-vision.md`](product-vision.md).

---

## 1. Principles (so the numbers survive an audit)

1. **Every emission number is traceable.** Each computed CO₂ value carries: the activity data
   it came from, the emission factor used (with its source + version + effective date), and the
   calculation method. No magic constants in code.
2. **Estimated ≠ measured — and we label which.** A number derived from a utility bill is an
   *estimate*; a number from a calibrated meter is *measured*. The data model records the
   `data_quality` of every input. Auditors and regulators care about this distinction.
3. **Emission factors are versioned reference data, not hardcoded.** Grid intensity changes
   yearly and varies by region (India CEA, IEA, national grids). Stored in a table with source
   and validity dates.
4. **No greenwashing.** "Avoided emissions" is presented as decision-support, never booked as a
   Scope 1/2 reduction. Credibility is the product.

---

## 2. The GHG Protocol in one table (the model we build to)

| Scope | What it covers | Factory examples we capture |
|---|---|---|
| **Scope 1** | Direct emissions from owned/controlled sources | **Diesel gensets**, gas boilers, company vehicles, refrigerant leaks |
| **Scope 2** | Purchased electricity / steam / heat | Grid electricity (× regional grid factor) |
| **Scope 3** | Everything else in the value chain | Purchased goods, transport, **embedded carbon of products** (CBAM), waste |

For these markets, **Scope 1 (diesel) and Scope 2 (grid)** are the bulk and the MVP focus.
Scope 3 / embedded carbon is built for CBAM in Phase 8a.

---

## 3. Data model (new tables, mirroring existing patterns)

Built alongside the current `Machine` / `SensorReading` / `Anomaly` schema.

| Table | Mirrors | Purpose |
|---|---|---|
| `Organization` | (new top level) | Tenant — the company |
| `Site` | above `Machine` | A physical plant; `Machine` gets a `site_id` |
| `EnergySource` | — | A source at a site: `grid` / `diesel_genset` / `solar` / `gas` |
| `EmissionFactor` | reference data | kgCO₂e per unit (kWh, litre diesel, …); `region`, `source`, `version`, `valid_from/to` |
| `UtilityBill` | `Dataset` | An uploaded/keyed electricity or fuel bill: period, kWh or litres, cost, `data_quality` |
| `FuelLog` | `SensorReading` | Genset runtime / diesel consumed per period |
| `EmissionRecord` | `Anomaly` | Computed: scope, activity, factor used, kgCO₂e, period, `data_quality`, source refs |
| `AvoidedImpact` | `MaintenanceLog` | When a recommendation is actioned: estimated kWh / CO₂ / downtime avoided |
| `RegulatoryReport` | `Recommendation` | A generated report: framework, period, payload, citations, status (draft/assured) |

`SensorReading` also gains an optional **`power_kw`** column so metered energy flows straight
into Scope 2.

---

## 4. Calculation flows

### Scope 2 — purchased electricity
```
kWh (from meter power_kw integrated, or from UtilityBill)
  × EmissionFactor(region grid, valid for period)
  = kgCO2e  →  EmissionRecord(scope=2)
```

### Scope 1 — diesel genset
```
litres diesel (from FuelLog, or estimated from runtime × rated consumption)
  × EmissionFactor(diesel combustion)
  = kgCO2e  →  EmissionRecord(scope=1)
```

### Energy-waste → carbon (the predictive-maintenance link)
```
baseline_kWh  = expected energy for this machine at this load (healthy baseline)
actual_kWh    = measured (or estimated from efficiency penalty implied by
                vibration/temperature anomalies at constant RPM)
wasted_kWh    = actual − baseline
wasted_CO2    = wasted_kWh × grid factor
₹/$ saved     = wasted_kWh × tariff
```
This is what links an `Anomaly` to a number the plant manager and the CSO both care about.

### Avoided impact (when maintenance is actioned)
On `MaintenanceLog.actioned = true`, estimate and store kWh/CO₂/downtime avoided →
`AvoidedImpact`. The maintenance log becomes a **carbon-savings ledger**, presented as
decision-support (not booked against the inventory).

---

## 5. Emission factors — sourcing

Seeded as versioned reference data; never hardcoded. Examples of source families:

- **Grid electricity:** India **CEA** CO₂ baseline database; IEA; national grid operators
  (Eskom for South Africa, TNB Malaysia, EGAT Thailand, etc.).
- **Fuel combustion (diesel, LPG, natural gas):** IPCC / GHG Protocol default factors.
- Each row: `region`, `activity_type`, `kgco2e_per_unit`, `unit`, `source`, `version`,
  `valid_from`, `valid_to`.

Updating factors yearly is a data operation, not a code change.

---

## 6. RAG extension — the compliance copilot

Reuse the existing ChromaDB + cited-answer pipeline, but tag ingested documents with a
`doc_type`:

- `manual` — equipment manuals (today's behaviour).
- `regulation` — GHG Protocol, ISSB S1/S2, CBAM guidance, BRSR framework, carbon-tax acts.
- `factor_source` — emission-factor datasheets.

Then the Copilot answers a new class of question, **grounded and cited**:
- "Is servicing PUMP-001 now material under ISSB S2?"
- "What activity data does a CBAM declaration need for our steel line?"
- "Which of this month's anomalies are reportable?"

The same citation discipline that grounds maintenance answers makes the **generated reports
defensible** — every figure links back to its source document and data row.

---

## 7. Report generator — one engine, many templates

```
EmissionRecord + activity data + RAG-cited methodology
        │
        ▼
   ReportEngine  ──►  template: CBAM | BRSR | ISSB S2 | SA carbon tax
        │
        ▼
   RegulatoryReport (PDF / structured bundle) + audit trail
```

Templates are pluggable; adding a country = adding a template, not rebuilding the engine.
Output carries the full traceability chain required for assurance (BRSR Core, CBAM verification).

---

## 8. Build order (maps to product-vision §7)

1. **Phase 6:** `EmissionFactor`, `UtilityBill`, `FuelLog`, `EnergySource`, `EmissionRecord`,
   `power_kw` column; Scope 1/2 calc; energy-waste link; dashboard tiles; CSV export.
2. **Phase 7:** `Organization`/`Site`, RBAC; sensor API ingestion.
3. **Phase 8:** `RegulatoryReport` + report engine; templates 8a CBAM → 8b BRSR → 8c SA → 8d SE Asia.
4. **Phase 9–10:** edge/scale + assurance ledger (see product-vision).
