"""Seed emission factors — versioned regional reference data.

These are sensible **defaults** so the product works out of the box. They are NOT
authoritative: grid intensities change yearly and vary by sub-region. Before any
report is filed they must be replaced with the operator's region- and year-specific
official factors (CEA for India, Eskom for South Africa, IEA, etc.). Each row carries
its own ``source`` so the provenance travels with every number computed from it.

Units:
- grid_electricity: kgCO2e per kWh   (Scope 2)
- diesel:           kgCO2e per litre (Scope 1)
- natural_gas:      kgCO2e per m3    (Scope 1)
- lpg:              kgCO2e per litre (Scope 1)
"""
from app.models import Scope

# region, activity_type, scope, kgco2e_per_unit, unit, source
SEED_FACTORS: list[dict] = [
    # --- Grid electricity (Scope 2), regional ---
    {"region": "IN", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.71, "unit": "kWh",
     "source": "CEA CO2 Baseline Database (India), approx. — replace with current year", "version": "default"},
    {"region": "ZA", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.95, "unit": "kWh",
     "source": "Eskom grid (South Africa), approx. coal-heavy — verify", "version": "default"},
    {"region": "MY", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.55, "unit": "kWh",
     "source": "Malaysia grid (Peninsular), approx. — verify with TNB/MGTC", "version": "default"},
    {"region": "TH", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.50, "unit": "kWh",
     "source": "Thailand grid, approx. — verify with TGO", "version": "default"},
    {"region": "ID", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.79, "unit": "kWh",
     "source": "Indonesia grid, approx. — verify", "version": "default"},
    {"region": "VN", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.62, "unit": "kWh",
     "source": "Vietnam grid, approx. — verify", "version": "default"},
    {"region": "NG", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.40, "unit": "kWh",
     "source": "Nigeria grid (gas-heavy), approx. — verify", "version": "default"},
    {"region": "KE", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.10, "unit": "kWh",
     "source": "Kenya grid (geothermal/hydro-heavy), approx. — verify", "version": "default"},
    {"region": "GLOBAL", "activity_type": "grid_electricity", "scope": Scope.SCOPE_2,
     "kgco2e_per_unit": 0.45, "unit": "kWh",
     "source": "Generic global average fallback — replace with local factor", "version": "default"},

    # --- Fuel combustion (Scope 1), region-independent (IPCC-style defaults) ---
    {"region": "GLOBAL", "activity_type": "diesel", "scope": Scope.SCOPE_1,
     "kgco2e_per_unit": 2.68, "unit": "litre",
     "source": "Diesel combustion, IPCC-style default ~2.68 kgCO2e/L — verify", "version": "default"},
    {"region": "GLOBAL", "activity_type": "natural_gas", "scope": Scope.SCOPE_1,
     "kgco2e_per_unit": 2.02, "unit": "m3",
     "source": "Natural gas combustion, default ~2.02 kgCO2e/m3 — verify", "version": "default"},
    {"region": "GLOBAL", "activity_type": "lpg", "scope": Scope.SCOPE_1,
     "kgco2e_per_unit": 1.51, "unit": "litre",
     "source": "LPG combustion, default ~1.51 kgCO2e/L — verify", "version": "default"},
]

# Typical small/medium diesel genset fuel burn, used to estimate litres from runtime
# hours when only runtime is logged. ~0.27 L per kWh; here expressed per running hour
# for a mid-size unit. Clearly an estimate — flagged as data_quality=ESTIMATED.
DEFAULT_GENSET_LITRES_PER_HOUR = 20.0
