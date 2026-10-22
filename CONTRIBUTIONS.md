# PRISM Team Contributions

This is the single record of individual project responsibilities and reviewable
contributions. Technical documents describe the system without attaching a team
member's name to their title or content. New phases should be appended here rather
than creating separate contribution files.

The tables record responsibilities for understanding, reviewing, improving,
testing, and presenting the work. Each member should keep
their own commit history and experimental evidence for work they personally review
or extend.

## Team

| Member | University ID | Continuing responsibility |
|---|---|---|
| Nishtha Jain | 22803007 | Data engineering and forecasting |
| Himangi Mishra | 22803016 | Dispatch, Q-learning, and explainability |
| Shrankhala Singh | 22803022 | Grid modelling, simulation, and faults |
| Gaurangi Tyagi | 22803012 | API, dashboard, and application integration |

## Phase 1: design and foundation

| Member | Contribution and artifacts | Individual review demonstration |
|---|---|---|
| Nishtha Jain | Measurement schema, synthetic measurement generator, preprocessing pipeline, data dictionary, source assessment, and quality audit | Explain provenance; reject an invalid CSV row; inspect gaps and the generated quality report |
| Himangi Mishra | Observation and action contracts, deterministic baseline dispatch, 270-state encoding, and RL design specification | Explain the state space, six actions, and proposed reward; demonstrate a reserve-limited recommendation |
| Shrankhala Singh | Grid schema and validation, NetworkX topology, Neo4j persistence adapter, resettable environment skeleton, and architecture | Validate connectivity and capacity rules; demonstrate isolated resets and an optional idempotent Neo4j import |
| Gaurangi Tyagi | Flask application, API contract, responsive dashboard, grid inspector, measurement charts, themes, and collapsible navigation | Run the application through Flask; inspect API responses; use the asset inspector, filters, charts, theme, and sidebar |

### Phase 1 shared evidence

- Synthetic network: 12 nodes, 12 edges, and 700 MW aggregate generation and
  demand.
- Synthetic history: 336 validated hourly rows generated with seed 42.
- Baseline recommendation and state encoding run without trained-model dependencies.
- The original Phase 1 suite contained 19 passing automated tests.
- Neo4j was verified by importing the same dataset twice without duplication.
- Desktop and mobile dashboard behavior was reviewed separately from backend tests.

## Phase 2: simulation and learning

### Checkpoint 1: executable backbone

| Member | Contribution and artifacts | Individual review demonstration |
|---|---|---|
| Nishtha Jain | Quarter-hour scenario adapter, persistence forecast, autoregressive forecast, chronological evaluation command, and dataset-method updates | Explain the chronological split and interpolation rule; run both baselines; interpret MAE/RMSE without treating synthetic metrics as real-grid accuracy |
| Himangi Mishra | Constrained dispatch integration, tabular Q-learning, valid-action masking, seeded training, Q-table persistence, and training command | Explain and reproduce the Q update; demonstrate masking; train, save, and reload a policy; explain why comparative evaluation is still required |
| Shrankhala Singh | Fifteen-minute environment transitions, generator and battery constraints, load shedding, scheduled faults, connectivity loss, rewards, and simulation tests | Demonstrate ramp and energy limits; inject and restore a plant or line outage; explain disconnected demand and the absence of electrical power flow |
| Gaurangi Tyagi | Forecast and scenario endpoints, request validation, OpenAPI update, integration tests, and Phase 2 application status | Call both endpoints; demonstrate invalid-input handling and synthetic-result labels; explain why learned dispatch remains disabled |

### Phase 2 checkpoint evidence

- The common implementation uses six actions and the 270-state encoding established
  in Phase 1.
- The suite contains 37 passing automated tests at this checkpoint.
- The default 500-episode Q-learning command completes and writes a versioned JSON
  artifact.
- Persistence and autoregressive forecasting evaluation runs on a chronological
  288-row training and 48-row test split.
- Forecast and scenario APIs return explicitly synthetic outputs.
- Learned dispatch and explanation endpoints remain unavailable until reviewed
  artifacts and comparative evidence are configured.

### Phase 2 completion record

| Member | Completed individual contribution | Reviewable evidence |
|---|---|---|
| Nishtha Jain | Expanded the deterministic fixture to 2,160 audited hourly rows; implemented and evaluated the NumPy LSTM against persistence and autoregression | Reproduce the 70/15/15 chronological split; inspect validation/test MAE and RMSE, model configurations, and SHA-256 checksums in `reports/phase2_forecasting.json` |
| Himangi Mishra | Completed five-seed Q-learning training, validation-based artifact selection, and paired comparison with the rule baseline | Reproduce seeds 11, 23, 42, 67, and 89; explain the held-out results in `reports/phase2_dispatch.json`, including why the learned policy remains non-executable |
| Shrankhala Singh | Defined the versioned normal, renewable-ramp, plant-fault, line-fault, and concurrent-fault suite and verified deterministic simulator behavior | Inspect `data/scenarios/phase2_scenarios.json`; replay both held-out scenarios and explain fault timing, partitioning, assumptions, and aggregate limitations |
| Gaurangi Tyagi | Completed the forecast and scenario dashboard, policy selection, fault controls, result charts, metric cards, and event log | Demonstrate all three forecasts, both policies, optional faults, responsive layouts, accessible status/error states, and browser verification |

### Phase 2 completion evidence

- The audited fixture contains 2,160 accepted hourly rows, with zero rejected rows,
  gaps, or imputations.
- Forecast artifacts cover all three targets and retain chronological validation
  and untouched test metrics. The LSTM beats persistence but not autoregression on
  the current synthetic test set.
- Five independent Q-learning seeds were compared with the rule baseline on the
  same held-out line and concurrent-fault scenarios. Q-learning slightly reduced
  mean unserved energy but produced worse mean return, curtailment, cost, and
  emissions; these negative findings remain part of the evidence.
- The selected seed-23 Q-table is available to the API and dashboard only as an
  experimental recommendation with `executable: false`.
- The completed suite contains 42 passing automated tests plus JavaScript, API,
  desktop, and mobile checks recorded in `docs/verification.md`.

Later phases must be appended below this section using the same member,
contribution, artifact, and evidence structure.

## Phase 3: integration — live-data increment

The following extends the team's continuing responsibilities and records the
artifacts and demonstrations for individual review.

| Member | Contribution and artifacts | Individual review demonstration |
|---|---|---|
| Nishtha Jain | Delhi SLDC field mapping, validation, provenance and source limitations in `prism/data/gridwatch.py` and `docs/data_sources.md` | Explain source timestamps, missing-data rejection, and why this feed does not replace the synthetic training history |
| Himangi Mishra | Integration boundary for the existing policy and forecast artifacts | Show that live readings are not silently supplied to models trained on synthetic data; XGBoost/SHAP remains pending |
| Shrankhala Singh | Separation of published Delhi measurements from the teaching topology and scenario state | Explain why drawal is not total generation and why the synthetic topology is not a Delhi network model |
| Gaurangi Tyagi | `/api/live/gridwatch`, minute cache, outage handling, IST timestamps and Delhi dashboard panel | Demonstrate real readings, manual refresh, stale/unavailable states, and unchanged synthetic workflows |

Verification: 51 automated tests and JavaScript syntax checks pass. A direct live
API smoke test returned HTTP 200 with validated source measurements. The dashboard
was checked in a browser against the live feed. This completes the read-only
display adapter, not the full Phase 3 integration or a historical-data collector.

### Phase 3 Step 1: report requirements audit — 2026-10-22

The requirements audit is recorded in `docs/PHASE3_REQUIREMENTS.md`, referencing
Review II, III and IV physical pages and report checksums. It maps the topology, data,
forecasting, dispatch, explanations, diagnosis, simulation, deployment and final
evidence requirements to current code and unmet acceptance criteria. This step
does not claim that any missing module has been implemented.

| Member | Assigned review responsibility | Reviewable artifact and evidence |
|---|---|---|
| Nishtha Jain | Review source eligibility, historical storage, 24-hour forecasting and retraining gaps | Data/forecast requirements, source checklist and forecast metric definitions |
| Himangi Mishra | Review XGBoost/Q-learning roles, objective definitions and SHAP evaluation gaps | Policy/explanation requirements and unresolved design/metric definitions |
| Shrankhala Singh | Review topology coverage, graph-schema limitations, diagnosis and simulation prerequisites | Topology completion gate and graph/simulation requirements |
| Gaurangi Tyagi | Review streaming/API/dashboard/deployment and system evaluation gaps | Integration requirements, ordered checkpoints and latency/throughput evidence criteria |

These are assigned review responsibilities; individual review is not asserted as
completed. Step 1 changes documentation only on the dedicated Phase 3 branch.
