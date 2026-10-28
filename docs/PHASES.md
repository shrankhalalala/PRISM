# PRISM phases and acceptance

Updated 2026-10-27. This is the single phase-status and target register.
**Phase 3 integration is implemented; full research acceptance remains partial.**
Passing software tests does not establish electrical validity or operating benefit.
Team responsibilities are in [CONTRIBUTIONS.md](../CONTRIBUTIONS.md), setup in
[INSTRUCTIONS.md](../INSTRUCTIONS.md), and demonstrations in [dashboard.md](dashboard.md#demonstration).

## Phase summary

| Phase | Delivered scope | Status and evidence |
|---|---|---|
| 1 — Foundation | Validated synthetic 12-node/12-edge, 700 MW network; 336 hourly measurements; preprocessing; baseline advice; Flask dashboard and optional Neo4j import | Complete for the declared prototype. Original verification: 19 tests. |
| 2 — Simulation and learning | 2,160-hour synthetic fixture; constrained 15-minute simulation; five fault/profile scenarios; persistence, AR and NumPy LSTM; five-seed Q-learning; integrated workspaces | Complete for synthetic research. Original verification: 42 tests. LSTM did not beat AR; learned dispatch did not improve overall outcomes. |
| 3 — Integration | Delhi reference evidence and telemetry; durable ingestion; real demand forecasts; surrogate/SHAP; investigation; jobs/reviews; retraining and Docker deployment | All 15 implementation milestones delivered. Latest suite: 126 tests. Acceptance gaps and scoped results below. |
| 4 — Evaluation | Physical validation, qualified operator studies and long-term deployment evaluation | Deferred by the user on 2026-10-27; no completion claim. |

Historical tests and measured outcomes remain in [verification.md](verification.md),
[phase2_forecasting.json](../reports/phase2_forecasting.json) and
[phase2_dispatch.json](../reports/phase2_dispatch.json).

## Requirements authority

Review II defines roles and initial goals; Review III adds detailed constraints;
Review IV's explicit refinements govern the implemented design. Page references
are physical PDF pages, with the cover as page 1. Supplied originals are outside
the repository; the audit recorded these identities:

| Report | File | Pages | SHA-256 |
|---|---|---|---|
| II | PBL-II Review-II.pdf | 18 | `36b905ee82adec4337dcf11352cc7ff9ae9caf3d8175f4f3e07eb7775db25c8b` |
| III | PBL-II Review-III (2).pdf | 14 | `be28187aac6dbd1eea6075719e82c04a73154ec15b6a3a4b560835f2a35c852b` |
| IV | PBL-II Review-IV (1).pdf | 18 | `81dce057cd42cab74a535569e581eefa7d8f794e8eed8e61dd3c98365f0c7487` |

II pp.3–6,12–16 covers topology, data, models, integration and targets. III pp.2–13
adds sizing, timing, lifecycle and uncertainty constraints. IV pp.8–10,13,17
refines model roles and records remaining work; IV p.2 separates integration from
evaluation. Requirement IDs below preserve the original audit's traceability.

### Accepted design and unresolved definitions

- **A01:** Delhi scope with documented external interfaces; no national-coverage claim.
- **A02:** Q-learning owns the six-action learned policy; XGBoost is its surrogate.
  III's five-class classifier is superseded by IV's six-action contract.
- **A03:** Forecast percentages use the same test cohort's actual peak; MAPE excludes
  actual demand below 1 MW. Frequency excursion versus standard deviation still
  needs a physical model and explicit measurement definition.
- **A04:** NumPy LSTM is IV's accepted implementation, not a missing TensorFlow port.
  III's 168-hour/128–64-unit/dropout/Adam design remains a scaling proposal; IV used
  24 hours, eight units, 12 epochs and clipped SGD. The 2026-10-27 residual variant
  preserves that lightweight architecture and is separately evaluated.
- **A05:** Validated public JSON adapters replace scraping empty JavaScript pages.
- **A06–A07:** Graph ranking is not physical causality; claimed manual-operation
  timings are not measured baselines. Synthetic rule comparisons remain labelled.
- **A08:** Conflicting 14-/16-week schedules do not establish a revised deadline.
- **A09:** Component licences and measured resource use govern deployment claims.

Use the chronological 70/15/15 split from IV, not III's older 80/20 split. IV's
MAE/RMSE are primary; II's MAPE <5% and III's 7% wording remain historical targets,
not interchangeable success criteria. One hour of retention is not 86,400 entries;
minute source updates are not six-second observations. The 12-node teaching graph
is retained rather than padded to an earlier proposed 20-node size.

## Phase 3 implementation milestones

| Steps | Delivered capability | Evidence |
|---|---|---|
| 1–7 | Report audit, Delhi boundary, source capture, inventories, uncertainty review, identity reconciliation and immutable Neo4j reference import | [Scope](DELHI_TOPOLOGY_SCOPE.md), [source archive](../data/sources/delhi/README.md), [reconciliation](../data/topology/delhi/RECONCILIATION.md), [import](DELHI_REFERENCE_IMPORT.md) |
| 8–9 | Inspectable 66 assets / 261 connection records; 49 station mappings; source/freshness flags | [Station report](../reports/phase3_station_feed.json), [dashboard](dashboard.md) |
| 10 | Redis streams, PostgreSQL history, deduplication, commit-before-ack recovery, quarantine and protected retention | [Streaming evidence](../reports/phase3_streaming.json), [ingestion](DURABLE_INGESTION.md) |
| 11 | Audited demand history, frozen 24-hour forecasts, validation selection and empirical intervals | [History audit](../reports/phase3_history_audit.json), [original forecasts](../reports/phase3_real_forecasting.json) |
| 12–13 | Six-action surrogate, actual TreeSHAP and graph/timing investigation | [Surrogate](../reports/phase3_surrogate.json), [explanations](../reports/phase3_explanations.json), [fidelity](../reports/phase3_shap_fidelity.json) |
| 14–15 | Durable jobs/cancellation, hourly refresh, advisory audit, retraining/promotion/rollback, seven-service deployment and demo deck | [Operations](../reports/phase3_operations.json), [lifecycle](../reports/phase3_retraining.json), [deployment](../reports/phase3_deployment.json), [deck](../deliverables/PRISM_Phase3_Demo.pptx) |

The 261 records comprise 245 dated circuit observations and 16 interface assertions,
not 261 verified current physical lines. Fifty qualifying Delhi asset identities
meet the reference count; they are not necessarily 50 separate physical sites.
Forty-nine geographic matches and 49 telemetry mappings are distinct coverage sets.
Seventeen unlocated assets remain in the directory until sourced coordinates arrive.
The initial six identity cases are resolved for reference purposes; electrical
readiness is separate. Synthetic Phase 2 fixtures and negative results are retained.

## Current requirement acceptance

“Implemented” describes software capability; “partial” means evidence needed for
full report acceptance is still missing. No historical source or synthetic fixture
is silently promoted to a current operating network.

| IDs | Requirement and current disposition |
|---|---|
| T01–T03 | Delhi boundary, plants/substations and transmission evidence: reference identities reconciled; current terminal/switching/ratings coverage partial. |
| T04–T05 | Versioned Neo4j import and full reference visualization verified; source snapshots and parallel observations preserved. Electrical-model import remains ineligible. |
| D01–D02 | Published aggregates and 49 station mappings implemented. Station loading is not plant output or a line limit; unmeasured assets remain explicit. |
| D03–D04 | Durable validated ingestion, recovery and PostgreSQL/history audit implemented. Full two-year coverage and real renewable histories remain missing. |
| F01–F02 | Real-demand LSTM/baselines and frozen 24-hour evaluation implemented. Current scoped MAE/RMSE targets pass; MAPE/interval coverage remain limited. Real solar/wind ineligible. |
| F03 | Weekly/drift reviews, validation gate, immutable bundles and rollback implemented; both rejection and improved real-candidate promotion demonstrated. |
| P01–P03 | Masked Q-learning, surrogate and paired synthetic objectives implemented. Richer-state candidates tested but rejected; real-network training and improved policy outcomes remain partial. |
| X01 | Actual surrogate attribution with provenance, agreement and abstention implemented; never explains a different Q action or physical causality. |
| G01 | Observed-alarm graph/timing ranking implemented; physical single/concurrent-fault causal accuracy unvalidated. |
| S01–S02 | Isolated recoverable what-if jobs and connectivity outages implemented; validated electrical cascade dynamics/prevention absent. |
| I01–I02 | Provenance-preserving APIs, forecasts, reviews, SHAP, jobs and source/service alerts integrated. Job queue panels temporarily hidden at the user's request; backend remains available. |
| I03–I04 | Local non-root Docker deployment, automated/browser checks, reports and editable eight-slide deck delivered. Public rollout, restore drills and full operator/physical evaluation deferred. |

## Current measured results

Forecast comparisons use 46 daily held-out origins × 24 hours = 1,104 values and a
peak of 8,122.56 MW. Candidates were selected on validation only. Because this test
cohort was previously reported, the refinement is retrospective, not prospective.

| Demand model | Test MAE / RMSE (MW) | MAE / RMSE (% peak) | MAPE |
|---|---|---|---|
| Original AR | 310.39 / 426.54 | 3.82 / 5.25 | 6.05% |
| Current direct AR | 296.68 / 389.21 | 3.65 / 4.79 | 5.73% |
| Original LSTM | 600.53 / 758.40 | 7.39 / 9.34 | 11.76% |
| Current residual LSTM | 365.49 / 498.46 | 4.50 / 6.14 | 7.09% |

The direct AR bundle passed the 1% validation improvement gate (355.156441 →
314.539981 MW RMSE) in local/Docker registries, retaining rollback. Nominal 90%
intervals covered 77.36% of test values; coverage is empirical, not guaranteed.
See [forecast refinement](../reports/phase3_forecast_refinement.json).

Rechecking 190 incomplete days yielded 180 responses, ten HTTP failures, no
conflicting timestamps and no recovered hours: 16,965 eligible hours / 555 gaps
remain. [Recovery evidence](../reports/phase3_history_recovery.json) preserves the
original dataset. Renewable history remains unavailable.

Six richer-state dispatch candidates used three seeds, two priors and 300 episodes
on 20 training profiles. None passed the per-scenario validation reliability gate
plus lower mean cost. On two historical test scenarios the best research candidate
averaged 690.32 MWh unserved / 635,681.25 synthetic cost units, versus baseline
755.01 MWh / 625,375.00. It is not promoted; Q/surrogate/SHAP artifacts are unchanged.
See [dispatch refinement](../reports/phase3_dispatch_refinement.json).

## Target register

These are scoped results, not a blanket claim of real-grid acceptance.

| ID / target | Current result and scope |
|---|---|
| M01 MAE <5% peak; M02 RMSE <8% peak | Current demand AR and LSTM pass on the cohort above; no renewable claim. |
| M03 MAPE <5% | Unmet; zero actual-demand exclusions in this cohort. |
| M04 dispatch accuracy >90% | 97.62% frozen-Q surrogate fidelity; accepted subset 99.46% at 96.28% coverage. Not optimality or operator agreement. |
| M05 cost reduction >10% | Unmet. Original 14 paired synthetic episodes: Q cost +14.44%, surrogate +9.30%; new candidate also fails acceptance. |
| M06 frequency within ±0.2 Hz | Not evaluable without validated frequency dynamics. |
| M07 SHAP fidelity >0.85 | Spearman 0.9515 on the declared 100-state ranking probe; off-manifold/permutation limitations remain. |
| M08 trust ≥4/5 | Unmeasured; qualified operator study deferred. |
| M09 causal detection >85%; M10 fault-to-cause <60 s | Physical accuracy and full workflow unverified; graph computation timing is not detection success. |
| M11 cascade prevention >80% | Not evaluable without validated cascade/intervention dynamics. |
| M12 end-to-end <5 s | Local API/job paths measured; sensor-to-real-dispatch chain ineligible. Source age is separate. |
| M13 Redis >10 updates/s | 1,200 synthetic events persisted over 60 s at 20/s; zero failures/drops/backlog; p95 15.68 ms. Burst 543.7/s over 200 events; not production saturation capacity. |
| M14 weekly/on-drift retraining | Implemented and verified; drift is a declared mean-shift proxy, not forecast-error drift. |
| R01 ≥50 nodes / scalable500+ | 50 qualifying Delhi identities; separate synthetic 600-node/1,200-edge import/query/browser checks pass. |
| R02 two real years | 730 requested days / 720 captured; 555 missing hourly values. Demand only. |
| R03 99.5% availability | Long-term observation deferred; health checks do not establish uptime. |
| R04 <4 GB/component; training ≤30 min | Observed peaks below 4 GB on an 8 GB host; original LSTM 4.85 s, refinement candidates 4.68–8.28 s. Limited workload. |
| R05 TreeExplainer100 / <100 ms | 100 training-only background rows; warm uncached p95 18.78 ms, cold initialization 1.40 s, separately reported. |
| R06 operator agreement ≥90% | Unmeasured; III's strict >90% wording also needs reconciliation before a survey. |
| R07 graph semantics | Verified Neo4j evidence; CONNECTED_TO weight1, PageRank0.85/10 iterations and residuals. No unsupported flow direction, SUPPLIES_TO/SERVES or GDS claim. |
| R08 engine <3 s / workflow <60 s | Local engine timing passes its scope; real cause correctness/full workflow unverified. |
| R09 6-second cadence / retention / expiry / <100 ms update | Minute collector, six-second durable read cache, protected one-hour stream retention, 24-hour dedup/forecast expiry. Not six-second source observations. |
| R10 API <1 s / recommendation <5 s | Ready-service benchmark records maxima/failures; model warmup before readiness. Real dispatch outcome unverified. |
| R11 operator lifecycle | Advisory accept/override, append records, recovery and hourly/weekly lifecycle implemented. Labels are assertions, not organizational identity. |
| R12 uncertainty / physics | Validation residual intervals and held-out coverage reported; electrical validity unmet. |
| R13 public inputs / free local stack | No paid service required; source access and component licence distinctions remain applicable. |
| R14 policy improvement | Unmet for real dispatch; no synthetic counterfactuals presented as physical evidence. |

Supporting measurements: [metrics](../reports/phase3_metrics.json),
[sustained ingestion](../reports/phase3_ingestion_sustained.json),
[resources](../reports/phase3_resources.json), [scalability](../reports/phase3_scalability.json),
[retraining cancellation](../reports/phase3_retraining_cancellation.json).

## Remaining work

1. Obtain verified terminal buses, switching snapshots, circuit identities and
   electrical parameters. [Eligibility audit](../reports/phase3_grid_eligibility.json)
   lists missing fields for all 245 circuit observations. Voltage layers do not
   infer transformer links or physical buses.
2. Acquire eligible missing demand/renewable observations without filling gaps
   synthetically; improve MAPE and interval coverage with independent validation.
3. Improve dispatch reliability and cost on validation before any replacement;
   real-network adaptation depends on electrical inputs.
4. Later: validate physical faults/frequency/cascades, conduct qualified operator
   studies, and measure deployment availability and restore behavior.

Latest software verification: 126 tests, Docker health and all three 24-hour model
APIs pass; cancelled candidate retraining preserves the active bundle. Earlier
browser checks cover responsive layouts/map interactions. Native PowerPoint
execution and a different-provider UI review were not verified.
