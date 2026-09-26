# Data contract

Current fixture: 2,160 hourly observations, 1 January–31 March 2026 UTC, fixed seed
42. These are generated teaching examples, not SLDC measurements, and are
insufficient for real-grid or seasonal claims. The static graph is a separate balanced example; its
700 MW snapshot is not synchronized with the historical sample series.

| Field | Type / unit | Validation / meaning |
|---|---|---|
| timestamp | ISO 8601 string | Explicit UTC offset required; normalized to UTC; hourly boundary; unique |
| demand_mw | float, MW | Finite, nonnegative aggregate demand |
| solar_mw | float, MW | Finite, nonnegative solar power |
| wind_mw | float, MW | Finite, nonnegative wind power |
| frequency_hz | float, Hz | Finite, 45–55 ingestion sanity range, not operational thresholds |
| source | string | Required provenance; sample is `synthetic_seed_42` |
| quality_flag | string, derived | `validated` only means these input checks passed |

Pipeline rejects all members of duplicate timestamp groups, invalid values, naive
timestamps, and off-hour timestamps. It sorts accepted rows and reports missing
hours without interpolation. Rejection reasons may overlap; their sum need not
equal rejected_rows. Raw input is retained. Validation does not prove authenticity.

No normalization or split is performed by the ingestion pipeline. Phase 2 uses a
chronological 70/15/15 experiment split and fits LSTM scaling only on training
data. Forecast target windows do not cross split boundaries. Do not fabricate
hourly observations from monthly aggregates. Solar-zero periods require a defined
percentage-error policy; always include MAE/RMSE.

Commands: `python -m scripts.generate_sample`, then `python -m scripts.prepare_data`.
Custom hourly CSV: `python -m scripts.prepare_data --input path.csv --output output/clean.csv --audit output/audit.json`.
