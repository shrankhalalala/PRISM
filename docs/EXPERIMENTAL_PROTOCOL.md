# Experimental Protocol: Phase 1 and Forward Evaluation Rules

## 1. Purpose

This protocol separates completed Phase 1 construction evidence from future model
performance experiments. Its immediate purpose is to verify that the research
software foundation is deterministic, internally consistent, and explicit about
unimplemented capability. It also fixes principles that later experiments must
follow before results are available.

## 2. Phase 1 research claims

Phase 1 supports only these claims:

1. The synthetic measurement fixture can be reproduced and validated under a
   declared hourly schema.
2. The synthetic initial topology satisfies declared structural constraints and can
   be loaded into NetworkX and idempotently persisted to Neo4j.
3. The baseline dispatch and Q-learning state encoding accept valid aggregate
   observations and reject invalid values according to their contracts.
4. The Flask API and dashboard expose the implemented fixtures and clearly report
   planned capabilities as unavailable.
5. The implementation passes its declared automated and manual checks.

Phase 1 makes no claim about forecasting accuracy, dispatch optimality, cost or
emission reduction, grid stability, fault-diagnosis accuracy, causal inference,
latency under production load, operator trust, uptime, or real-world safety.

## 3. Phase 1 hypotheses and acceptance criteria

| ID | Construction hypothesis | Acceptance criterion | Evidence |
|---|---|---|---|
| P1-H1 | Valid hourly measurements are preserved deterministically | All 336 generated rows accepted; zero gaps and zero imputation | Quality audit and pipeline tests |
| P1-H2 | Invalid measurement cases are rejected observably | Tests cover missing fields, invalid values, duplicates, naive timestamps, and off-hour timestamps | Unit tests |
| P1-H3 | The initial graph contract prevents malformed topology | Tests cover valid counts, bad endpoints, excess plant output, duplicates, and disconnection | Grid tests |
| P1-H4 | Environment instances do not share mutable state | Mutating one instance does not alter another or the source; reset restores the fixture | Environment test |
| P1-H5 | Dispatch outputs expose their limited feasibility scope | Hold, shortage, surplus, validation, and state-encoding cases pass; all recommendations remain non-executable | Dispatch tests |
| P1-H6 | API behavior is explicit and reproducible | Read endpoints succeed; malformed inputs fail; planned endpoints return 501; missing fixtures return 503 | API tests |
| P1-H7 | Neo4j persistence is idempotent | First and second isolated imports each return 12 nodes and 12 edges | Disposable-container integration check |
| P1-H8 | The dashboard remains usable across target layouts | Data, selection, chart range, theme, sidebar, containment, and console checks pass | Browser verification record |

## 4. Test environment

The recorded Phase 1 verification used macOS, Python 3.12, the package versions in
`requirements-tested.txt`, Node for JavaScript syntax validation, and Neo4j 5.26
Community for the disposable persistence check. The dashboard runs through Flask's
development server on loopback. This is a development environment, not a
production deployment benchmark.

## 5. Automated procedure

Create and activate the environment as described in `README.md`, then run:

```bash
python -m scripts.generate_sample
python -m scripts.prepare_data
python -m unittest discover -s tests -v
node --check prism/static/dashboard.js
```

Expected construction evidence:

- 336 accepted measurement rows;
- 0 rejected rows, detected gaps, and imputed rows for the reference fixture;
- 12 graph nodes and 12 graph edges;
- 700 MW aggregate generation and 700 MW aggregate demand in the static fixture;
- 19 passing automated tests; and
- successful JavaScript syntax validation.

The missing-fixture test intentionally emits an application error log while
asserting the expected HTTP 503 response. That log is not a failed test.

## 6. Neo4j integration procedure

With Docker available, run:

```bash
python -m scripts.verify_neo4j
```

The script pulls the declared Community image, creates a randomly named temporary
container bound to loopback, waits for connectivity, imports the same dataset twice,
checks for 12 nodes and 12 edges after both imports, and removes the container.
Image availability and Docker startup are external prerequisites.

## 7. Dashboard verification procedure

Start the application with `python -m prism` and verify:

1. the synthetic-data badge and grid totals are visible;
2. selecting plant, substation, and load assets updates the inspector;
3. asset filters emphasize only the requested category;
4. 24-hour and 7-day views contain 24 and 168 observations respectively;
5. demand, solar, and wind controls update the chart and caption;
6. sidebar and theme preferences survive a reload;
7. the mobile drawer opens, closes with Escape, and hides inactive navigation from
   keyboard focus;
8. the graph scrolls within its panel without widening the document;
9. refresh and partial-failure messages are understandable; and
10. the browser console contains no application errors during the checked flow.

## 8. Data retention and evidence

Each future experiment should receive an immutable identifier and retain:

- source-data checksums and quality audit;
- code commit hash;
- environment/package record;
- configuration and random seeds;
- trained model checksum;
- raw per-scenario outputs;
- aggregate metrics and confidence intervals; and
- figures or tables generated from those raw outputs.

Results should never be copied manually into the paper without a traceable result
artifact or script.

## 9. Rules for Phase 2 and later experiments

### 9.1 Forecasting

- Use chronological train, validation, and untouched test periods.
- Fit scalers and imputers only on training data.
- Compare LSTM against at least persistence and a simple statistical or linear
  baseline on identical horizons.
- Report MAE and RMSE in physical units. Predefine any percentage-error treatment
  for zero or near-zero actual output.
- Report performance by target, horizon, and relevant operating period rather than
  only one aggregate score.

### 9.2 Dispatch and Q-learning

- Apply identical feasibility constraints and scenario seeds to the rule-based and
  learned policies.
- Separate training, validation, and test scenarios at the episode level.
- Use multiple independent training seeds and report variability, not only the best
  run.
- Report unserved energy, operating cost, emissions, constraint violations,
  curtailment, and return separately.
- Record invalid-action masking and any fallback or override as part of the result.

### 9.3 XGBoost surrogate and SHAP

- Generate surrogate data from a frozen policy.
- Keep evaluation episodes independent of surrogate training records.
- Report overall agreement, per-action precision/recall, confusion matrix, and
  performance in rare fault states.
- Label SHAP output as an explanation of the surrogate class score.
- Report disagreements and feasibility overrides instead of hiding them.

### 9.4 Fault diagnosis

- Keep injected fault identity hidden from the diagnosis algorithm.
- Define single and concurrent fault scenarios before evaluation.
- Report detection rate, false attribution, ranking position, and elapsed diagnosis
  time on identical scenario sets.
- Use PageRank only as structural evidence; causal claims require event and
  observation evidence.

## 10. Statistical reporting

Later model comparisons should report the number of independent runs or scenarios,
mean or median as appropriate, dispersion or confidence intervals, and paired
comparisons when policies see the same scenarios. Hyperparameters and success
thresholds must be fixed before the final test set is inspected. Negative and
inconclusive outcomes remain part of the research record.

## 11. Phase 1 result summary

The recorded Phase 1 run passed 19 automated tests, JavaScript syntax validation,
two consecutive Neo4j imports without duplication, and the documented dashboard
checks. These results demonstrate a reproducible project foundation. They are not
evidence that PRISM has yet achieved its proposed forecasting, dispatch,
explainability, or diagnosis objectives.

## 12. Phase 2 checkpoint protocol: 2026-09-26

The first Phase 2 increment implements the simulator, forecasting baselines, and
tabular Q-learning trainer. Construction acceptance for this checkpoint is:

| ID | Check | Acceptance criterion |
|---|---|---|
| P2-C1 | Profile adapter | Two hourly rows produce eight ordered quarter-hour points without modifying input |
| P2-C2 | Generator dynamics | Dispatch respects the 25 MW command quantum and configured ramp/capacity/minimum limits |
| P2-C3 | Battery dynamics | Charge and discharge respect energy, power, efficiency, and state-of-charge bounds |
| P2-C4 | Fault dynamics | Scheduled outages activate and restore at deterministic steps; disconnected demand is reported |
| P2-C5 | Episode lifecycle | Termination occurs exactly at the configured horizon and post-terminal steps are rejected |
| P2-C6 | Q-learning | Seeded training is reproducible, updates the table, masks invalid actions, and round-trips through JSON |
| P2-C7 | Forecasting | Persistence and autoregression return finite nonnegative forecasts; MAE/RMSE are reproducible |
| P2-C8 | API integration | Forecast and scenario routes validate inputs and return explicitly synthetic results |

Run the checkpoint with:

```bash
python -m unittest discover -s tests -v
python -m scripts.evaluate_forecasting
python -m scripts.train_q_learning --episodes 500
```

The automated suite currently contains 37 passing tests. The default 500-episode
training command and the chronological forecasting evaluation have also completed.
Their numerical outputs are implementation evidence only. Phase 2 is not complete
until LSTM comparison, multiple independent Q-learning seeds, held-out scenario
evaluation, trained-policy API activation, and dashboard simulation controls have
been implemented and reviewed.

## 13. Phase 2 completion protocol and results: 2026-09-26

The requirements named at the checkpoint are now implemented. Reproduce the final
evidence with:

```bash
python -m scripts.generate_sample
python -m scripts.prepare_data
python -m scripts.evaluate_forecasting
python -m scripts.evaluate_q_learning --episodes 500
python -m unittest discover -s tests -v
node --check prism/static/dashboard.js
```

| ID | Completion criterion | Recorded result |
|---|---|---|
| P2-F1 | Larger audited fixture | 2,160/2,160 rows accepted; zero gaps and imputations |
| P2-F2 | Frozen forecast partitions | Chronological 1,512 train / 324 validation / 324 test |
| P2-F3 | Three forecast methods | Persistence, 24-lag autoregression, and four-gate NumPy LSTM evaluated with MAE/RMSE |
| P2-F4 | Multi-seed policy comparison | Five independent seeds; identical validation and held-out test scenarios |
| P2-F5 | Versioned scenario suite | Normal, renewable ramp, plant fault, line fault, and concurrent fault with SHA-256 |
| P2-F6 | Reviewed policy activation | Seed 23 selected only on validation return; API output is non-executable |
| P2-F7 | Interactive application | Forecast and scenario controls, metrics, trajectories, event logs, responsive layouts |
| P2-F8 | Construction verification | 42 automated tests, Python compilation, JavaScript syntax, API, and browser checks pass |

The LSTM beats persistence but trails autoregression for every target on the test
partition. Across paired held-out runs, Q-learning slightly reduces mean unserved
energy (743.862043 versus 755.006330 MWh) but has worse mean return (-154.285003
versus -120.584628), curtailment, cost, and emissions. These outcomes are retained
without post-test retuning. Phase 2 therefore demonstrates a complete reproducible
comparison pipeline, not forecast dominance or dispatch superiority.
