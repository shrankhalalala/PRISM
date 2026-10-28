# Audited real demand and 24-hour evaluation

`python -m scripts.acquire_demand_history` captures one public Delhi SLDC load
curve per requested day, at no more than one request per second, with bounded
retries, size limits, original bytes, checksums and a resumable manifest.
`--retry-failed` retries only failed days and verifies existing captures. The
requested range is 2024-10-22 through 2026-10-21. Raw originals remain local under
`data/sources/delhi/2026-10-23-demand-history/raw/`; the committed manifest records
URLs and fingerprints so acquisition can be reproduced. Failed HTTP responses
remain gaps; they are not evidence that the original day had no demand.

`python -m scripts.prepare_demand_history --postgres` verifies every available raw
hash and prepares UTC timestamps from published local FORDATE/TIMESLOT, explicitly
assuming Asia/Kolkata. ENTRYDATE is not the observation time. Only Delhi/MW rows
at five-minute times qualify. Conflicting duplicates are excluded; a valid hourly
mean requires at least ten distinct observations out of twelve. All requested
calendar hours remain present, with missing values for ineligible hours. No
interpolation or synthetic replacement occurs. Versioned PostgreSQL hourly rows
preserve their dataset checksum and sample-count/quality fields.

`python -m scripts.evaluate_real_forecasting` freezes a chronological 70/15/15
split by calendar time. Training fits the NumPy LSTM's normalization on training
values only. Training windows cannot cross timestamp gaps. Validation/test origins
are daily, with 24 observed context hours and 24 observed target hours. All 24
predictions are recursive from the frozen origin: no future actual values enter
the prediction horizon. Incomplete blocks are excluded and counted. Validation
RMSE selects among persistence, autoregression and the documented NumPy LSTM.
All test results are retained even when LSTM underperforms. Per-horizon MAE/RMSE,
training duration, peak process RSS, model/data hashes and source dates are saved.

Empirical uncertainty uses validation-only absolute residual 90th percentiles,
separately per horizon. Held-out coverage is reported; a nominal 90% band is not
a guarantee. This is not a calibrated physical grid confidence interval.

`GET /api/forecast/real` returns 24 predictions, origins, data/model provenance,
source age and explicit stale-history status. `model=lstm`, `autoregressive` or
`persistence` selects a reviewed model. Redis forecast entries expire after 24 hours
and keys include data/model content hashes. The origin age is recomputed each call.
The historical acquisition is not a continuous current load-curve refresh. The
hourly background cycle added later must refresh history before claiming current
forecasts. Real solar/wind requests return 422 because no audited history exists.
The synthetic three-target Phase 2 endpoint remains separately labeled.

## Refinement and recovery — 2026-10-27

`python -m scripts.refine_real_forecasting` compares two direct ridge settings and
three seasonal-residual LSTMs against the preserved baseline. Direct regression
predicts all 24 departures from yesterday at once using 24 observed hours and
known calendar covariates. The LSTM predicts the departure from the same hour
yesterday; its original behavior remains the default for old artifacts.
Selection is written before test evaluation. The test cohort was previously
reported, so these are retrospective results. The validation-selected direct
model reaches 389.21 MW test RMSE; the selected LSTM reaches 498.46 MW.

`python -m scripts.promote_forecast_refinement` rechecks data identity and candidate
validation scores, refuses incumbent overlap with validation, and uses the existing
1% promotion gate with rollback. API model names and 24-hour responses remain
unchanged. Scheduled retraining now compares recursive/direct autoregression and
the residual LSTM on validation, retaining the incumbent when improvement fails.

`python -m scripts.recover_demand_history --output <new-directory>` recaptures days
with insufficient hourly coverage, preserves original bytes and rejects conflicting
timestamps across captures. The 2026-10-27 run recovered no additional hours; its
report is `reports/phase3_history_recovery.json`. It does not overwrite the frozen
training CSV or substitute synthetic renewable observations.
