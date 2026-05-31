# Power BI Data Model

Two export endpoints produce clean, flat CSVs for Power BI ingestion:

- `GET /api/export/sensors.csv` → processed sensor readings
- `GET /api/export/anomalies.csv` → detected anomalies

## `pdm_sensors.csv`

| Column | Type | Notes |
|---|---|---|
| machine | text | machine name (e.g. PUMP-001) |
| timestamp | datetime | ISO-8601 reading time |
| temperature | number | °C (normalized) |
| pressure | number | bar |
| vibration | number | mm/s RMS |
| rpm | number | revolutions/min |
| temperature_roll_avg | number | engineered rolling average |
| pressure_roll_avg | number | engineered rolling average |
| vibration_roll_avg | number | engineered rolling average |
| rpm_roll_avg | number | engineered rolling average |

## `pdm_anomalies.csv`

| Column | Type | Notes |
|---|---|---|
| machine | text | machine name |
| parameter | text | temperature / pressure / vibration / rpm |
| timestamp | datetime | anomaly time |
| value | number | reading value |
| z_score | number | standard deviations from mean |
| severity | text | HIGH / MEDIUM / MONITOR |
| is_trending | boolean | worsening trend flag |

## Suggested model

- Relationship: `pdm_anomalies[machine]` → `pdm_sensors[machine]` (many-to-one to a
  derived Machine dimension).
- **Executive fleet view**: card visuals for HIGH/MEDIUM counts, a matrix of
  machine × severity, and a line chart of `value` vs `timestamp` with anomaly markers
  from `pdm_anomalies`.
- Suggested measures: `Anomaly Count = COUNTROWS(pdm_anomalies)`,
  `High Severity = CALCULATE([Anomaly Count], pdm_anomalies[severity]="HIGH")`.
