# Phase 3 requirements and completion checklist

Audit date: 2026-10-22. Work is isolated on the dedicated Phase 3 branch.
Pushed Phase 2 baseline: `e4209a4` (includes the Phase 2 completion commit
`e698de0` and subsequent setup documentation).

This is Step 1 of the agreed implementation sequence. It records requirements,
gaps, dependencies, and acceptance evidence; it does not implement later steps.
Current status includes the live Grid Watch display increment on this
branch. That increment is not part of the pushed Phase 2 baseline.

## 1. Requirements authority and status rules

Sources: the supplied Review II, III and IV reports, located beside the repository.
Page numbers refer to physical PDF pages, starting with each cover as page 1.

| Report | File | Pages | SHA-256 |
|---|---|---|---|
| II | PBL-II Review-II.pdf | 18 | `36b905ee82adec4337dcf11352cc7ff9ae9caf3d8175f4f3e07eb7775db25c8b` |
| III | PBL-II Review-III (2).pdf | 14 | `be28187aac6dbd1eea6075719e82c04a73154ec15b6a3a4b560835f2a35c852b` |
| IV | PBL-II Review-IV (1).pdf | 18 | `81dce057cd42cab74a535569e581eefa7d8f794e8eed8e61dd3c98365f0c7487` |

Review I provides literature context. Review II specifies roles, data strategy and
targets. Review III adds detailed design parameters, diagrams and constraints.
Review IV records implementation and explicit refinements of Review III, notably
its Table 11 on page 13. Use those explicit refinements for the current design;
preserve earlier goals that were deferred rather than claiming they were met or
silently cancelled. Remaining conflicts are listed in Section 9.

Sections 2-5 trace the original Review II baseline unless a report is explicitly
named. Section 9 adds the Review III/IV requirements and cross-report review.
Existing repository decisions explain implementation history; they do not silently
replace report requirements. Verified topology remains the first implementation
priority. The report cross-check changed documentation only; Step 2's scope and
source specification is now recorded in [DELHI_TOPOLOGY_SCOPE.md](DELHI_TOPOLOGY_SCOPE.md).

Statuses describe the requirement as a whole:

- **Partial:** a useful foundation exists, but report acceptance is unmet.
- **Missing:** no implementation/evidence fulfilling the requirement was found.
- **Needs definition:** the report's wording needs an operational definition
  before its metric or design can be evaluated fairly.
- **Verified complete:** implementation and its declared acceptance evidence both
  exist. None of the full integration requirements below has this status yet.

A passing test suite is evidence about implemented behavior, not proof that all
report requirements or performance targets have been achieved. Individual team
accountability remains in [CONTRIBUTIONS.md](../CONTRIBUTIONS.md).

## 2. Topology: the first implementation milestone

| ID | Report requirement and pages | Current evidence/status | Remaining work and completion evidence |
|---|---|---|---|
| T01 | Delhi/India grid scope; Delhi narrowing permitted (II 4-5); minimum 50 Delhi nodes and 500+ scalability (III 2, 11) | Partial: [grid.json](../data/raw/grid.json) is explicitly fictional, with 12 nodes and 12 edges; IV 13 records this as an implementation refinement | Document the Delhi boundary, voltage levels, source dates, and external supply connections. Reconcile all source assets and report coverage against the 50-node goal; do not fabricate assets to reach it. Define a separate 500+ node scalability test. |
| T02 | Plants and substations as graph nodes (5, 13) | Partial: four fictional plants, four substations, four load zones | Create a source-backed inventory with stable IDs, official names, aliases, types, locations/voltage/capacity where available, provenance, and verification state. Reconcile every source asset within T01. |
| T03 | Transmission lines as graph edges; topology from CEA/NPP (5, 13-14) | Partial: 12 generated connections with synthetic MW ratings | Catalogue confirmed endpoints, circuit IDs, voltage, and verified ratings where available. Preserve parallel circuits and transformer relationships where supported by the source. Trace every edge to evidence; flag ambiguities. |
| T04 | One-time topology ingestion into Neo4j (14) | Partial: [Neo4jStore](../prism/grid/neo4j_store.py) seeds the teaching dataset | Add a separate versioned Delhi dataset and reproducible ingestion command. Compare imported IDs/properties/counts with the inventory. Import twice without duplication or changes to synthetic data. |
| T05 | Real grid-state visualization (5) | Partial: [dashboard.js](../prism/static/dashboard.js) renders a small schematic | Make every imported node and connection accessible through navigation, search, pan/zoom, filters, and inspection. Identify boundary assets, provenance, and unavailable measurements. Record browser verification at desktop/mobile sizes. |

### Topology prerequisites discovered in the current code

[model.py](../prism/grid/model.py) uses `networkx.Graph`, rejects duplicate endpoint
pairs, requires positive MW ratings for every line, requires plant output values,
and requires one connected initial topology. These rules suit the synthetic
fixture but must not force fabricated information into an official inventory.

Before importing real assets, separate asset metadata from optional telemetry,
support parallel circuits and the required asset types, and represent unknown
ratings as unknown. Investigate islands and missing links rather than connecting
them artificially. Display-only assets with incomplete electrical parameters must
not silently enter simulation as fully specified equipment.

### Topology completion gate

- [x] T01 boundary and reference source versions are recorded in the Step 2 scope specification; inventory completeness remains pending.
- [ ] Every plant/substation in that reference boundary is reconciled to a stable ID.
- [ ] Every documented connection is represented or explicitly listed as unresolved.
- [ ] Circuit identity, aliases, duplicate records, and endpoint consistency are audited.
- [ ] Missing values and uncertainty remain visible; no invented topology/ratings.
- [ ] Neo4j imports reproduce the inventory and preserve other datasets.
- [ ] Every imported asset and connection is accessible in the dashboard.
- [ ] Coverage counts, unresolved items, source checksums, and verification evidence are saved.

An inventory with unresolved connections may be a reviewable partial milestone;
it must not be labeled a fully verified topology or electrical model. No expected
node inventory is set until the source boundary is established. Review III sets
a minimum 50-node Delhi goal; Review IV records the current 12-node prototype,
not completion of that goal. The reports give source references, asset types and
fictional prototype names, not a complete real station inventory. Count plants,
substations, load zones and boundary representations separately.

## 3. Data, forecasting, dispatch, simulation, and integration

| ID | Report requirement and pages | Current evidence/status | Remaining work and completion evidence |
|---|---|---|---|
| D01 | SLDC live frequency/load/interchange/source generation (12) | Partial: [gridwatch.py](../prism/data/gridwatch.py) exposes demand, frequency, drawal, and schedule with source time and freshness | Audit the additional published fields and their meaning. Record coverage, units, timestamps, source access conditions, missingness, and recoverable collector failures. Do not interpret drawal as total generation. |
| D02 | Substation load, voltage, and area distribution (12) | Missing: no verified asset telemetry mapping | Audit the SLDC station/area feeds after T01-T05. Resolve aliases to graph IDs; distinguish distribution-company areas from substations. Publish mapping coverage and unmatched IDs; unavailable telemetry stays unavailable. |
| D03 | Redis streaming ingestion (4, 14) | Missing: the display adapter has a transient per-process minute cache | Add a collector, validated event schema, stream producer/consumers, deduplication, retry/backoff, replay/recovery, retention, and health reporting. Verify restart and duplicate-event behavior. |
| D04 | Historical acquisition and PostgreSQL preprocessing storage (12-14) | Partial: synthetic CSVs and [pipeline.py](../prism/data/pipeline.py); no PostgreSQL | Audit appropriate real datasets, preserve provenance/raw records, define canonical timestamps/units and missingness policy, implement storage/migrations and reproducible preparation. Demonstrate a source-to-training-data audit. |
| F01 | LSTM for 24-hour demand/solar/wind forecasts (II 3-5; III 9); NumPy refinement (IV 8-9, 13) | Partial: [NumPy LSTM](../prism/forecasting/lstm.py), three synthetic targets, API horizons up to 24; framework choice is consistent with IV | Retain the documented NumPy baseline; audit real-data eligibility and evaluate true 24-hour horizons. Scale the model only with supporting data/evidence. Save configuration, training-only normalization, split, seeds, checksums and version. TensorFlow migration is not a mandatory correction under IV. |
| F02 | MAE/RMSE/MAPE evaluation (II 5, 14); IV 13 adopts MAE/RMSE because of zero solar output | Partial: [evaluate_forecasting.py](../scripts/evaluate_forecasting.py) evaluates one-step walk-forward MAE/RMSE on synthetic history, as documented in IV | Retain MAE/RMSE as the current reported metrics. Evaluate fixed 24-hour origins without actual future observations inside the horizon. Any additional MAPE target needs a declared applicable target and zero-output policy; do not force it onto nighttime solar. A 24-value API response alone is not 24-hour evaluation evidence. |
| F03 | Weekly or drift-triggered retraining (16) | Missing | Define schedule/drift signal, train/validation selection, artifact review/promotion, rollback, and logs. Demonstrate a triggered run without test leakage or silently promoting an inferior model. |
| P01 | Q-learning state/action/reward design and training (5) | Partial: [Q-learning](../prism/dispatch/q_learning.py), six actions/270 states, [five-seed evidence](../reports/phase2_dispatch.json) on synthetic scenarios | Check suitability for the expanded topology, define/revise state and constraints, retrain on partitioned scenarios, and report convergence, returns, variability, action masking, and paired baseline outcomes. Retain Phase 2's negative results. |
| P02 | XGBoost dispatch model (II 3, 5, 14-15; III 10), refined to Q-policy surrogate (IV 2, 13, 17) | Missing implementation; model role is clarified by IV | Implement the XGBoost surrogate of the frozen Q-policy with independent episode splits and the current six-action contract. Report action-level errors and operating outcomes. Do not reinstate III's five classes without a documented mapping/design change. |
| P03 | Multi-objective cost/stability/emission trade-offs (5) | Partial: [environment.py](../prism/simulation/environment.py) includes synthetic cost/emissions, balance and unserved-energy penalties; no frequency dynamics | Document physical/economic assumptions and objective weights, run sensitivity and paired comparisons, and separate constraint feasibility from electrical stability. Real ratings/operating parameters need provenance. |
| X01 | SHAP for all dispatch recommendations (5) | Missing: `/api/explain` returns 501 | Explain the correct model output/action with feature values, attribution semantics and provenance. If using a surrogate, show agreement/disagreement and never use its explanation to justify a different served action. Verify attribution consistency and failure/unavailable states. |
| G01 | PageRank risk propagation and BFS/DFS causal tracing (3, 5) | Partial: topology reachability and explicit fault events exist; no diagnosis engine | Define PageRank graph/weights and event evidence, implement ranked diagnosis using observations and timing, hide injected identities from the algorithm, and evaluate single/concurrent faults. Structural centrality is not proof of causation. |
| S01 | Celery what-if simulation (5) | Partial: resettable constrained synthetic simulator and synchronous `/api/scenario`; no Celery | Add isolated background jobs, submission/status/results/cancel/failure behavior and worker-restart handling. Keep configurations and scenario seeds reproducible. Integrate real topology only where required parameters are known. |
| S02 | Controlled fault/cascade evaluation (15-16) | Partial: [five-scenario suite](../data/scenarios/phase2_scenarios.json) covers faults, not electrical cascade dynamics | Define diagnosis observations, propagation/cascade rules, intervention policy, matched baseline, held-out scenarios, denominators and timing. Do not relabel reachability loss as a simulated electrical cascade. |
| I01 | Flask REST APIs and end-to-end integration (5-6) | Partial: forecast/dispatch/scenario APIs and [OpenAPI](openapi.json) exist; no integrated live-model pipeline | Connect eligible data to versioned models, explanations, jobs and diagnosis. Preserve source/asset/time provenance; verify schema contracts, errors, partial failures and recommendations remaining non-executable. |
| I02 | Real-time dashboard, SHAP charts and alerts (5) | Partial: synthetic workbenches and separate live readings; no SHAP/diagnosis/alert workflow | Integrate topology, data freshness, forecasts, recommendations, explanations, job progress and evidence-backed alerts. Verify accessibility and desktop/mobile complete flows. |
| I03 | Docker deployment on the stated local/free infrastructure (3-5) | Partial: [compose.yaml](../compose.yaml) starts optional Neo4j only; Flask is a development server | Package the application, worker, Redis, PostgreSQL and Neo4j with health checks, configuration/secrets instructions, persistent data and clean startup/shutdown. Record actual hardware/resource use; do not assume the report's 16 GB feasibility claim is verified. |
| I04 | Testing, evaluation, final report/PPT/demo (6, 14-16) | Partial: [verification](verification.md), reproducible Phase 2 artifacts and live-adapter checks | Add evidence for each implemented requirement and target below, retain failed/inconclusive results, reconcile report claims with actual behavior, and assemble the final demonstrations. Full performance evaluation/final packaging follow implementation. |

## 4. Source acquisition checklist (verification belongs to later steps)

The following are the report's proposed sources, not a declaration that each
currently provides a usable API, licence, field set, or sampling guarantee.

| Report source | Intended role | Current acquisition status |
|---|---|---|
| Delhi SLDC Grid Watch (12) | Live aggregates and source generation | Four-field display adapter checked on 2026-10-22; additional field coverage, permitted reuse and historical collection remain open. |
| Delhi SLDC Redirect dashboard (12) | Station/area telemetry | Not integrated or verified in this step. |
| NPP transmission map (13) | Connectivity, circuits and boundary flows | Not acquired; validate actual field availability and map date. |
| NPP capacity map (13) | Plant capacities, fuel and status | Not acquired; distinguish installed capacity from current output. |
| ICED plant details (13) | Plant inventory and metadata | Not acquired; verify coverage, exports, terms and identifiers. |
| CEA maps, Delhi/NCR (13) | Stations and transmission connections | Not acquired; identify authoritative map version/boundary before claiming completeness. |
| Ember electricity data (13) | Historical generation/demand | Not acquired; verify cadence, geography and target coverage rather than assuming hourly Delhi data. |
| CEEW energy access dataset (13) | Potential demand features | Not acquired; survey observations are not automatically time-aligned grid telemetry. Verify relevance before inclusion. |

Use [data_sources.md](data_sources.md) as the acquisition/provenance record. Record
why a proposed dataset is unsuitable and what alternative is used; do not silently
claim that all listed sources were integrated.

## 5. Report targets and required measurement evidence

Every target below is **unverified against the report's intended real/integrated
system**. This is the original Review II target register, preserved for
traceability. Section 9 records changed targets in III and explicit refinements
in IV; superseded values must not be treated as simultaneous active requirements.
Synthetic Phase 2 results remain useful engineering evidence. Targets are not
promises or completed acceptance claims.

| ID | Report target | Page | Evidence required before reporting an outcome |
|---|---|---|---|
| M01 | Forecast MAE < 5% of peak load | 14 | Frozen evaluation periods; MAE in MW and declared peak-load denominator per target. Resolve applicability to renewable targets in A03. |
| M02 | Forecast RMSE < 8% of peak load | 14 | Same origins/targets as M01; RMSE in MW and normalized value with denominator. |
| M03 | Forecast MAPE < 5% | 14 | Correct percentage-error definition, declared zero/near-zero policy, excluded-sample counts, per-target/horizon results. |
| M04 | Dispatch accuracy > 90% | 14 | Predeclared ground-truth/reference-action definition, independent test episodes, overall and per-action metrics/confusion matrix. Report policy fidelity separately from operating quality. |
| M05 | Cost reduction vs baseline > 10% | 15 | Same unseen scenarios, feasible actions, prices and accounting; per-run cost and paired reduction distribution. No substitution of assumed manual timings for measured costs. |
| M06 | Frequency deviation < +/-0.2 Hz | 15 | Resolve standard-deviation versus excursion ambiguity; justified frequency model and sampled trajectories. Live frequency display does not show simulated dispatch improves stability. |
| M07 | SHAP fidelity score > 0.85 | 15 | Define correlation/ranking/aggregation and permutation experiment before final evaluation; report uncertainty. This is separate from Q-learning/XGBoost action agreement and SHAP additivity. |
| M08 | Operator trust score >= 4/5 | 15 | Structured clarity survey, participant qualifications, sample size, questionnaire and summarized responses. Student feedback must not be labeled operator feedback. |
| M09 | Root-cause detection rate > 85% | 15 | Predetermined single/concurrent faults; identities hidden from diagnosis; definition of correct detection, denominator, false attribution and missed diagnoses. |
| M10 | Mean time to root cause < 60 seconds | 15 | Define wall time versus simulation time and start/end events. Record latency distribution, misses and timeout policy without dropping failures. |
| M11 | Cascade prevention rate > 80% | 16 | Explicit cascade/intervention model, matched baseline and seeds, cascade eligibility denominator and per-scenario results. Requires S02, not just fault restoration. |
| M12 | End-to-end latency < 5 seconds | 16 | Timestamp ingestion through displayed recommendation; report distribution and conditions. Report upstream observation age separately; minute source cadence cannot imply sub-five-second sensor freshness. |
| M13 | Redis throughput > 10 updates/second | 16 | Defined events, sustained controlled replay/load test, duration, concurrency, processed/failed/dropped/backlogged counts and hardware. Do not poll SLDC at this rate to manufacture load. |
| M14 | Retraining weekly or on drift | 16 | Scheduled/drift run log, source window, artifact version, validation/promotion decision and rollback evidence. |

## 6. Design differences and definitions to resolve

Record resolutions in [DECISIONS.md](../DECISIONS.md) and update the affected
protocol before model training/final testing. These items do not block preparing
the topology inventory; they block claims or implementations that depend on them.

| ID | Difference/ambiguity | Proposed treatment; not a claim of completion |
|---|---|---|
| A01 | Report proposes national scope with Delhi fallback; user requests complete topology first | Define a Delhi source boundary in Step 2, including relevant external supply assets. State exclusions and record this scope decision; do not claim national coverage. |
| A02 | II/III call XGBoost a dispatch classifier; IV 13 explicitly retains it as a Q-policy surrogate | Model-role ambiguity is resolved by IV: Q-learning owns learned recommendations, XGBoost explains through a surrogate. Implementation and fidelity evidence remain missing; action agreement does not establish dispatch quality. |
| A03 | Evaluation definitions are incomplete or inconsistent | Freeze peak-load normalization, correct MAPE averaging/zero policy, action labels, SHAP/permutation correlation, and the frequency-deviation statistic. The frequency target mixes standard deviation and signed excursion notation; report both once modeled, rather than silently choosing an easier metric. |
| A04 | II/III propose TensorFlow/Keras and a larger LSTM; IV 4, 8-9, 13 documents the compact NumPy refinement | Treat NumPy as the current reported design. Keep larger architecture/history goals traceable; any scaling/framework change requires an experiment/design decision rather than automatic replacement. |
| A05 | Report names BeautifulSoup/Scrapy; live source is a JavaScript app backed by JSON | Reuse the observed public JSON endpoint with validation rather than scrape empty HTML. This is an implementation substitution, not a completed Redis collector. Record access/source limitations. |
| A06 | Report links PageRank to causal propagation and asks for stability/cascade metrics | Separate structural ranking, observation-based diagnosis, electrical dynamics and intervention outcomes. Specify additional models/parameters; mark unsupported metrics not evaluable until those prerequisites exist. |
| A07 | Report uses manual dispatch/diagnosis times as comparison baseline | Treat these timings as report context until supported by measurements. Use reproducible rule-based simulations for engineering comparisons and label them accurately; do not claim measured superiority to human operators. |
| A08 | Report describes both 14-week and 16-week scheduling | Do not silently infer a revised delivery date. Track completion by milestones and reconcile the final schedule with the team when scheduling work. |
| A09 | Report lists technologies as open-source and hardware as feasible | Verify selected component licensing/distribution and actual resource use during packaging. Do not claim Neo4j PageRank availability/configuration or complete-stack feasibility solely because basic Neo4j seeding works. |

## 7. Ordered delivery checkpoints and dependencies

These checkpoints implement the previously agreed 15 steps; grouping does not
change their order. A checkpoint is checked only after its evidence is saved.

- [x] **Step 1:** report-to-code checklist, target register, gaps and dependencies
  documented here. No source acquisitions or runtime changes required.
- [x] **Step 2:** define Delhi scope, voltage levels, source boundary and dates (T01); see [DELHI_TOPOLOGY_SCOPE.md](DELHI_TOPOLOGY_SCOPE.md). This does not complete the real asset inventory or the 50-node goal.
- [x] **Step 3:** acquire/audit topology references and preserve provenance; see the [source archive](../data/sources/delhi/README.md). All required DTL captures succeeded; optional access/coverage gaps remain recorded. This does not complete the asset inventories.
- [x] **Step 4:** build the source-referenced node inventory (T02); see the [node inventory](../data/topology/delhi/README.md). All 47 directory rows and 258 endpoint occurrences are accounted for; unresolved identities remain explicit for Steps 5-6. No full current-Delhi completeness or 50-node verification claim.
- [ ] **Step 5:** build and verify edge/circuit inventory (T03).
- [ ] **Step 6:** audit completeness/uncertainty before further model integration.
- [ ] **Step 7:** adapt schema/validation and import the Delhi graph into Neo4j (T04).
- [ ] **Step 8:** display and inspect every imported asset/connection (T05).
- [ ] **Step 9:** map eligible telemetry to verified assets (D01-D02).
- [ ] **Step 10:** implement Redis/history infrastructure (D03-D04, I03 foundation).
- [ ] **Step 11:** audit real history, train and evaluate 24-hour forecasts (F01-F02).
- [ ] **Step 12:** apply IV's policy/surrogate roles; adapt/retrain/evaluate dispatch (P01-P03).
- [ ] **Step 13:** implement SHAP and graph diagnosis with independent evidence (X01, G01).
- [ ] **Step 14:** background simulations, alerts and complete operator flow (S01-S02, I01-I02).
- [ ] **Step 15:** retraining lifecycle, deployment, full metric evaluation and final
  evidence/report/PPT/demo (F03, I03-I04, M01-M14).

Keep legacy synthetic scenarios reproducible while building the real graph. A
real asset inventory does not by itself provide power-flow parameters, fault
ground truth, operating limits, cost curves, or a valid dispatch training set.

## 8. Evidence and change discipline

For each completed requirement retain source-data/topology versions, code commit,
environment, configurations, seeds, artifact checksums, raw outcomes and generated
summary metrics as applicable. Use [EXPERIMENTAL_PROTOCOL.md](EXPERIMENTAL_PROTOCOL.md)
for evaluation rules and extend it before new experiments.

All new implementation belongs on the dedicated Phase 3 branch; preserve `main` at
the pushed Phase 2 baseline. Stage only intended files for each coherent commit.
Keep existing `.prism-ppt-build/` material outside unrelated commits. A future
push should set this branch's own upstream, not target `origin/main`.

Step 1 verification: checked Review II pages 3-6 and 12-16 against the listed code,
configuration and stored evidence; subsequently reviewed Review III and IV,
including the design diagrams and refinement table. Verified report checksums and branch base.
Documentation links/requirement IDs and whitespace are checked separately. No
new test run or refreshed live-source availability is claimed by this audit.

## 9. Review III and IV cross-check — 2026-10-22

This section updates the initial Review II-only audit. The new reports were read,
including III's architecture/class/sequence/state/use-case diagrams on pages 4-8
and IV's implementation-refinement Table 11 on page 13. This is documentation
review only; it does not implement the requirements below or advance Step 2.

### 9.1 Explicit refinements: use the current reported design

| Topic | Earlier report design | Review IV record | Effect on the checklist |
|---|---|---|---|
| Policy and surrogate | III 10: five XGBoost classes (Coal, Gas, Battery, NoAction, LoadShed), confidence >75% | IV 8-10, 13, 17: Q-learning with six actions; XGBoost retained as a Q-policy surrogate | A02 is resolved as a model-role question. Implement a six-action surrogate or explicitly document any aggregation. Five classes and Q-policy action agreement are not interchangeable. Define confidence/abstention for the surrogate before using III's threshold. |
| LSTM implementation | III 9: 168-hour look-back, layers 128/64, dropout 0.2, dense 32, Adam 0.001, MSE, 50 epochs, batch 32 | IV 8-9, 13: NumPy, 24-hour window, 8 units, 12 epochs, clipped SGD | Existing lightweight model is a documented refinement, not an unapproved framework substitution. No automatic TensorFlow migration. Larger-model settings remain historical/scaling candidates requiring sufficient data and evaluation. |
| Forecast metrics | II 14: MAPE <5%; III 2, 9: MAPE <=7%, with <7% in III 13 | IV 13: MAE/RMSE in MW because solar has zero nighttime output | Preserve III's historical 7% target and II's older 5% target, but use IV's MAE/RMSE as the current evaluation design. Resolve normalization/any target-specific percentage goal before new experiments. MAPE is not a statistical confidence interval. |
| Split | III 9: 80/20 train/test | IV 8, 13: 70/15/15 chronological, separate validation | Keep the chronological validation split; do not revert to 80/20 simply to match the older design. |
| History | III 2: minimum two real years; III 3 acknowledges possibly six usable months | IV 13: 90 synthetic days, real-data integration ongoing | The smaller dataset is an acknowledged prototype limitation, not proof of seasonal/real-grid performance. Audit obtainable coverage before claiming the earlier history goal or changing it. |
| Graph | III 2, 11: minimum 50 Delhi nodes, scalable to 500+ | IV 6-7, 13, 16: 12-node teaching network, larger real-data network ongoing | Treat 50 nodes as an unmet design goal; completeness must also reconcile the official source boundary. Do not inflate counts with invented assets or duplicate aliases. |
| Phase assignment | II/III propose an integrated system and targets | IV 2: Phase 3 integration, Phase 4 evaluation | Keep construction gates and full research evaluation separate. IV 17 specifically retains live ingestion, Redis, surrogate/SHAP, diagnosis and policy improvement as ongoing work. |

### 9.2 Additional constraints and evidence now tracked

These extend T01-T05, D01-D04 and the other requirements above. They are not
completed merely because IV describes the earlier prototype.

| ID | Additional requirement / source | Current status and required evidence |
|---|---|---|
| R01 | >=50 Delhi nodes and 500+ scalability (III 2-3, 11) | Partial: 12 synthetic nodes. Verify real coverage, publish counts by asset type, and separately test 500+ graph import/query/rendering. A scalability fixture must be labeled synthetic and cannot establish Delhi inventory completeness. |
| R02 | At least two real years for seasonal LSTM training (III 2); IV 13 defers real data | Unmet. Record observed date range, cadence, quality, geography, target coverage and gaps. Synthetic augmentation/interpolation is not an equivalent measured two-year history. |
| R03 | 99.5% availability (III 2, 13) | Unmeasured. Define service boundary, observation period, probes, planned downtime and numerator/denominator. A health endpoint or successful demo is not uptime evidence. |
| R04 | <4 GB memory per component; <=30 min per LSTM training run on a 16 GB machine (III 2) | Unmeasured. Record hardware, workload/model size, peak memory by component and complete training duration. Preserve the CPU-only prototype unless a change is justified. |
| R05 | TreeExplainer, local human-readable features, stated 100 samples/decision; explanation <100 ms (III 11) | Missing. Define how the sample/background setting applies to the chosen TreeExplainer mode, feature schema, timing scope and cache behavior. Benchmark real inference, not only cached responses. |
| R06 | Operator explanation agreement >=90% (III 2, 11), >90% in III 13 | Unmeasured; distinct from II's mean trust >=4/5 and policy-surrogate agreement. Define survey population, question, sample size and denominator; reconcile inclusive/strict threshold before evaluation. |
| R07 | Neo4j relations SUPPLIES_TO / CONNECTED_TO / SERVES, weights 0-1, PageRank damping 0.85 and 10 iterations (III 5, 11-12) | Missing relative to design: current adapter stores LINE relationships. Define relation semantics/direction, transformer/circuit representation, weight provenance and convergence checks. Undirected connectivity or normalized utilization does not prove flow direction or calibrated risk. |
| R08 | Causal engine <3 s (III 12); fault-to-cause <60 s (III 2, 13; II 15) | Missing diagnosis engine. Preserve both timing requirements with defined scopes, e.g. compute time and full detection workflow; record actual definitions rather than silently relaxing the stricter value. |
| R09 | Redis XREAD; 6-second cadence, 1-hour retention, 24-hour cache expiry; <100 ms/update (III 12) | Missing. The existing page/JSON feed was observed refreshing on a minute cadence; the report's 6-second source claim is unverified. Establish actual source cadence, stream event rate, retention semantics, forecast freshness and measured processing latency. |
| R10 | API <1 s and dispatch/query-to-recommendation <5 s (III 2, 13) | Unmeasured. Separate cached/uncached API latency, ingestion-to-display latency and upstream data age. Retain failures/timeouts in performance reports. |
| R11 | Accept/override dispatch, audit log, health, degraded/recovery states, hourly forecast cycle and weekly/drift retraining (III diagrams 4-8) | Partial UI/API foundation; operator decision records and full lifecycle missing. Add an auditable advisory workflow, model/data provenance and recovery evidence. Accepting a recommendation records a human decision; it must not introduce equipment switching. |
| R12 | Forecast confidence intervals and physics validation (III 3); repeated scenarios/uncertainty in sequence diagram (III 6) | Missing calibration/physics evidence. Declare uncertainty method and coverage evaluation; define simulator fidelity and repeated-run protocol. Classifier confidence, MAPE, source frequency and aggregate connectivity are not substitutes for power-flow validation. |
| R13 | Public-data-only inputs and zero software cost; documented/tested container deployment (III 3-4) | Partial: public fixture/feed, test suite, documentation and optional Neo4j container. Audit source access, chosen package licensing, whole-stack setup and actual resource use; no proprietary internal SLDC data is needed. |
| R14 | Policy improvement through reward reweighting, richer state and live-profile retraining (IV 17) | Pending. Preserve the Phase 2 baseline/results; define new state/weights and data eligibility, tune on training/validation only, then evaluate paired held-out outcomes. Real measurements do not supply counterfactual dispatch labels or dynamics automatically. |

### 9.3 Conflicts and report statements requiring care

- III 12 calls retention both one hour and 86,400 entries. Those are not
  equivalent without an event rate: one stream publishing once per six seconds
  generates 600 entries/hour. Define time retention and entry caps separately.
- III 10 says ten input features but its textual list names nine feature groups;
  the class diagram on III 5 instead distinguishes coal and gas available MW.
  Freeze one explicit schema consistent with the actual Q-policy and explain it.
- III 10 uses `softmax` while asking for a confidence threshold. Specify how
  class probabilities are obtained and validated if that threshold is retained.
- III 3 describes a synthetic 20-node starting graph; IV documents 12 nodes.
  Keep the current 12-node dataset as historical baseline, not a missing-asset
  list to be repaired by adding eight fictional nodes.
- IV 6 says the hourly validation pipeline can be reused unchanged for live data,
  but it rejects off-hour timestamps. A minute/second stream needs a separate
  observation contract and an explicit hourly aggregation adapter for training.
  The current display adapter also uses a different frequency sanity range
  (40-60 Hz) from the hourly pipeline (45-55 Hz); reconcile/document source and
  model-ingestion checks rather than treating either as an operating safety band.
- IV 9's no-infeasible-action language is limited to the implemented aggregate
  constraints; it does not establish electrical feasibility of a real network.
- III's timing-improvement factors, approximate cascade baseline and six-second
  source assertion are report claims, not measurements established by this audit.
- III/IV diagrams and tables specify component types and the fictional prototype
  inventory; they do not supply the complete real Delhi station/line inventory.

### 9.4 Effect on the next step

Topology remains first. Step 2 must identify an official source boundary and
record the 50-node design goal, with separate plant/substation/load/boundary counts
and a later 500+ scalability check. The NumPy LSTM, six-action policy and
chronological validation split remain the current reported baseline. XGBoost is
a Q-policy surrogate. No new topology data, runtime code, model training or
infrastructure changes were made during this report review.
