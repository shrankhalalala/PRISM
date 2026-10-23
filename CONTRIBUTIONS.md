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

### Phase 3 Step 2: Delhi topology scope and source selection — 2026-10-22

`docs/DELHI_TOPOLOGY_SCOPE.md` defines the 400/220 kV Delhi reference boundary,
other-owner and external-supply inclusion rules, source dates and remaining
acquisition gaps. `DECISIONS.md` records ADR-015. Official DTL station/circuit
pages and its dated existing/planned maps were inspected; no real graph was
imported and no runtime behavior changed.

| Member | Continuing review responsibility | Reviewable artifact and evidence |
|---|---|---|
| Nishtha Jain | Source dates, field provenance and acquisition/telemetry limitations | Audited source register and distinction between source date and measurement freshness |
| Himangi Mishra | Boundary and unknown-parameter implications for policy inputs | Separation of real asset identity, telemetry and simulation eligibility |
| Shrankhala Singh | Station/line boundary, circuit identity and completeness rules | Scope specification, historical/planned-map distinction, unresolved identity issues and ADR-015 |
| Gaurangi Tyagi | How the eventual reference graph will be labeled and inspected | Display scope and source/status requirements; existing synthetic dashboard remains unchanged |

Step 2 establishes the scope and source-selection gate. It does not claim the
50-node goal, complete inventories, electrical validation, or individual review
completion. Source archiving and inventory construction are subsequent steps.

### Phase 3 Step 3: source acquisition and evidence preservation — 2026-10-22

The dated local archive in `data/sources/delhi/2026-10-22` records original-source
fingerprints, retrieval metadata, source locators and explicit failed/access-only
outcomes. `scripts/acquire_topology_sources.py` captures into new directories and
verifies existing archives offline. Original files remain local; the project
records document acquisition and reuse limitations. The runtime grid is unchanged.

| Member | Continuing review responsibility | Reviewable artifact and evidence |
|---|---|---|
| Nishtha Jain | Source capture, provenance, access failures and historical date handling | Catalog, manifest, acquisition script and offline integrity checks |
| Himangi Mishra | Suitability limits for plant/policy metadata | Filing/index references and distinction between real observations and counterfactual policy inputs |
| Shrankhala Singh | Map/table/circuit evidence and other-owner interface references | Seventeen extraction locators, BBMB page reference and unresolved connectivity/identity register |
| Gaurangi Tyagi | Reproducible acquisition setup and source/application separation | Archive guide, snapshot protection and structured capture failure handling |

Verification includes 58 passing automated tests and offline checks of the saved
files/locators. This records a source-evidence milestone, not completed inventories,
50 verified nodes, resolved optional-source gaps, or individual review completion.

### Phase 3 Step 4: source-referenced node inventory — 2026-10-22

`data/topology/delhi` records 64 inventory entries with stable project IDs and
source-qualified identity rules. All 47 DTL directory rows, 46 transformation
observations and 258 endpoint occurrences are retained. Uncertain site identities,
historical/proposed status and an unassigned SOW observation remain explicit.

| Member | Continuing review responsibility | Reviewable artifact and evidence |
|---|---|---|
| Nishtha Jain | Source encodings, dates, provenance and missing-value handling | Source-bound evidence records and deterministic JSON/CSV extraction |
| Himangi Mishra | Keep operating/model inputs separate from inventory metadata | Unknown available MW/output, simulation eligibility and plant/substation distinctions |
| Shrankhala Singh | Identity reconciliation, multi-owner records and node coverage | Stable-ID rules, 47-row coverage, supplemental records and eight open node issues |
| Gaurangi Tyagi | Inspectable inventory artifacts and reproducible commands | Inventory guide, CSV, coverage summary, rebuild/check command and contract tests |

The full suite passes 67 tests, and inventory regeneration matches the saved
outputs. This step does not claim 64 distinct verified sites, 50 verified nodes,
validated circuits, individual review completion, or a changed live dashboard.

### Phase 3 Steps 5–6: circuit observations and completeness audit — 2026-10-22

The offline circuit builder retains all 129 later and 113 historical DTL line-table
rows plus three named BBMB circuit observations. Separate source-qualified
narrative claims preserve historical ring, LILO and boundary references without
creating inferred electrical links. JSON/CSV, provenance fingerprints and a
readable audit document the evidence and uncertainty.

| Member | Continuing review responsibility | Reviewable artifact and evidence |
|---|---|---|
| Nishtha Jain | Source dates, historical transcription and numerical-unit handling | Dated observations, archive fingerprints, portion-length handling and unknown MW limits |
| Himangi Mishra | Electrical/model eligibility and report acceptance limits | No inferred operating parameters; explicit hold on electrical/model import |
| Shrankhala Singh | Parallel circuits, duplicate labels, endpoint/site reconciliation and coverage | Circuit inventory, source-specific aliases, issue register and historical comparisons |
| Gaurangi Tyagi | Reproducible extraction, inspectable outputs and integration boundary | Rebuild/check command, CSV, audit Markdown and contract tests |

The audit was performed and its acceptance gate has not passed. Individual review
completion, complete real-network coverage, 50 verified nodes, current operating
connectivity and website/database/model integration are not claimed.

### Phase 3 reconciliation and Step 7 reference ingestion — 2026-10-22

Four additional DTL references support a separate review overlay: SOW attribution
and Timarpur nominal voltage are corroborated, circuit multiplicities are clarified,
and Budella/Dwarka status limitations remain visible. Six node issues still require
reconciliation. Original source extraction and the initial audit stay preserved.

| Member | Continuing review responsibility | Reviewable artifact and evidence |
|---|---|---|
| Nishtha Jain | Follow-up source dates and reconciliation evidence | Four verified captures, review locators and unchanged original records |
| Himangi Mishra | Reference/electrical eligibility boundaries | Unknown operating fields, simulation rejection and electrical gate held open |
| Shrankhala Singh | Versioned reference schema, circuit identities and Neo4j consistency | MultiGraph validation, immutable dataset namespace and exact endpoint/property checks |
| Gaurangi Tyagi | Local import workflow, repeatability and preservation checks | Export/import CLI, setup guide, live repeat-import verification and non-secret evidence report |

All 82 tests pass. Live Neo4j checks verify repeat import, preservation of both
existing test fixtures and rejection of a corrupted snapshot. The dedicated local
reference database contains the reviewed snapshot. Individual review completion,
full electrical topology, 50 verified sites and website integration are not claimed.

### Topology identity correction and report-count reconciliation — 2026-10-22

Official DTL, POWERGRID, BBMB, NRPC and regulator documents now support decisions
for all six original node cases. The corrected reference export merges supported
aliases, preserves owner-specific portions and raw source records, classifies planned
Budella separately and records documented generation/bus/boundary interfaces.
Review III's 50 Delhi substation/plant node requirement is distinguished from
geographic-site counting. Corrected reference coverage contains 50 qualifying
Delhi asset identities without aliases, the extra Narela portion or external assets.

| Member | Continuing review responsibility | Reviewable artifact and evidence |
|---|---|---|
| Nishtha Jain | Source dates, archive integrity and historical change records | Captured evidence, page locators, fiscal/date limitations and dated observations |
| Himangi Mishra | Topology identity versus electrical simulation requirements | Explicit source-value unknowns, planned asset handling and preserved simulation boundary |
| Shrankhala Singh | Alias/ownership/bus identities, plant interfaces and report coverage | Canonical mappings, corrected asset CSV, 15 historical findings and 50-node counting list |
| Gaurangi Tyagi | Reproducible exports, immutable import and inspection artifacts | Generated reconciliation review, reference CLI and repeat-import preservation report |

All 87 tests pass. The corrected local Neo4j version was imported twice and the
prior version verified unchanged. Individual review completion, complete current
operating coverage and real electrical model readiness are not claimed.

### Phase 3 Step 8: reference-grid inspection — 2026-10-23

The dashboard now exposes the complete reviewed reference snapshot: 66 assets,
245 circuit observations and 16 interface assertions. Search, filters, pan/zoom,
asset and connection ledgers preserve provenance and unknown operating values.
Nishtha's source-date review, Himangi's electrical eligibility review, Shrankhala's
identity/coverage review and Gaurangi's integration/reproducibility review remain
individual review responsibilities. Ninety tests pass; desktop/mobile inspection
and independent interface review passed. This does not certify operating topology.

### Phase 3 Step 9: source-qualified station telemetry — 2026-10-23

Forty-nine explicit source labels map to reference assets. The live capture matched
49/49 with no rejected/unmatched labels; 17 assets remain without eligible station
measurements. API and inspector retain signed MW/MVAr, voltage, source timestamps,
raw RTU status, quality limits and stale/unavailable handling. Source identity,
electrical interpretation, mapping coverage and integration remain the same four
members' respective review responsibilities. All 93 Step 9 tests and independent
browser review pass. Station loading does not establish plant output or line limits.

### Phase 3 Step 10: durable ingestion — 2026-10-23

Redis Streams and PostgreSQL now retain validated immutable observations with
content identity, context, recovery and commit-before-ack behavior. Local live
verification covers duplicates, crash replay, quarantine, protected pending/unread
retention and real station history. The labeled 200-event synthetic benchmark
measures 543.7 events/s and 2.69 ms p95 locally; this is not upstream performance.
The same source/electrical/mapping/integration review responsibilities continue.
Ninety-five tests pass. Long-term uptime and deployment durability remain unmeasured.

### Phase 3 Step 11: audited real demand forecasting — 2026-10-23

The 730-day requested range yields 720 captured days and 203,870 valid five-minute
observations after bounded retries. Hourly means preserve 555 missing/ineligible
hours; PostgreSQL verifies all 17,520 calendar rows. Models cannot bridge timestamp
gaps. Frozen 24-hour forecasts use 70/15/15 calendar splits, training-only LSTM
normalization, validation selection and independent test origins. Autoregression
is selected; LSTM underperformance and empirical interval coverage are retained.
The same four source/electrical/coverage/integration review responsibilities apply.
Ninety-eight tests pass, and real forecast/cache/stale-origin checks pass. No real
solar/wind eligibility, complete two-year measurements or operational validity is claimed.

### Phase 3 Step 12: six-action policy surrogate — 2026-10-23

XGBoost now imitates the frozen Q-policy with explicit ten-feature semantics,
whole-episode chronological separation, validation selection, six output classes,
masking and score-based abstention. Held-out fidelity is 97.62%, distinct from
operator agreement and dispatch effectiveness. Paired baseline/Q/surrogate
simulation outcomes and all class support/confusion counts are retained.
The same source/electrical/coverage/integration review responsibilities continue;
real-grid eligibility and policy improvement remain unestablished.
