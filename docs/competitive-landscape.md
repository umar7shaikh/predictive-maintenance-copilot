# Competitive Landscape

> Who already builds pieces of this, what to borrow from each, and the gap we fill.
> Strategy lives in [`product-vision.md`](product-vision.md); carbon engine in [`esg.md`](esg.md).

> Note: smaller players' feature sets and status change fast. Treat the named tools as
> **categories to study**, not gospel, and verify all regulatory specifics (BRSR Core fields,
> CBAM data requirements) against current official guidance before hardcoding them.

## The market, by category

**1. Carbon accounting / ESG reporting (the "report" half)**
Watershed, Persefoni, Sweep, Plan A, Normative, Greenly — polished Western SaaS for EU/US
enterprises with clean data. Microsoft Sustainability Manager, IBM Envizi, SAP Sustainability
Footprint Management, Salesforce Net Zero Cloud — enterprise giants, heavy and costly. Workiva,
Novisto, Diligent ESG — disclosure/filing workflow.

**2. India / emerging-market ESG (closest geography)**
Updapt, Sustainext, ESGDS — India-focused ESG data + BRSR reporting. Most direct geographic
comparable; proves a paying India market exists. Reporting-only — never touch the machines.

**3. CBAM-specific (the export wedge)**
CarbonChain — embedded carbon for metals/commodities, aimed at CBAM. SAP and Persefoni have
CBAM modules.

**4. Predictive maintenance / industrial IoT (our current strength)**
Augury, Samotics (SAM4), Senseye (Siemens), Waites, Falkonry, Uptake, SymphonyAI; IBM Maximo,
GE Proficy, PTC ThingWorx for big asset-performance platforms.

**5. Energy management (EMS)**
Schneider EcoStruxure, Siemens, Honeywell, Verdigris, GridPoint.

## Study hardest

- **Samotics (SAM4)** — derives **both** condition (failure prediction) **and** energy-efficiency
  loss from a motor's electrical signals. Closest to our "every anomaly has a carbon shadow"
  thesis, already commercialized.
- **Schneider EcoStruxure** — the most complete "energy + sustainability + asset" platform; just
  heavy and enterprise-priced.

## The gap nobody fills (our product)

| Capability | Who has it | Combines it for OUR market |
|---|---|---|
| Predictive maintenance | Augury, Samotics | — |
| Energy waste → savings | EcoStruxure, Verdigris | — |
| Carbon + multi-reg reporting (CBAM, BRSR, SA, SE Asia) | Watershed, Updapt, CarbonChain | — |
| Built for SME factories with bad internet, diesel gensets, no sensors, low budget, local languages, on-prem | **~nobody** | **← us** |

Western platforms are costly, assume clean metered data + good connectivity, and don't generate
BRSR or a South-African carbon-tax filing. India ESG tools do BRSR but never touch the floor or
save energy. PdM tools predict failures but produce no carbon report.

**Our wedge:** the only tool that starts on the factory floor (saving the owner money — the hook
to get them paying) and from the same data produces the **specific local regulatory report** for
India / Africa / SE Asia / EU-export — usable even by a factory whose only data is an electricity
bill and a diesel receipt.

## What to borrow from whom

- **Updapt / Sustainext** → BRSR report structure + India compliance UX.
- **CarbonChain** → CBAM embedded-carbon methodology.
- **Samotics** → energy-from-maintenance-signal (technical core).
- **Watershed / Persefoni** → trustworthy "audit trail + methodology" presentation.
- **Schneider EcoStruxure** → energy + carbon + assets in one dashboard.
