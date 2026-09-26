# PRISM Methodology: Phase 1 Foundation

## 1. Purpose and scope

Phase 1 establishes a reproducible foundation for later experiments in forecasting,
dispatch, reinforcement learning, explainability, and graph-based fault diagnosis.
The implemented work validates data and software contracts; it does not evaluate
the predictive or operational performance of learned models.

The methodological principle for this phase is separation of concerns: data
validation, topology validation, state representation, API behavior, persistence,
and presentation are tested independently before they are connected to trained
models or a dynamic simulator.

## 2. Reproducible synthetic study environment

The repository contains two independent fixtures:

1. A 336-observation hourly time series covering 1–14 January 2026 UTC. It contains
   demand, solar generation, wind generation, and frequency fields generated with
   fixed random seed 42.
2. A static 12-node teaching network containing four plants, four substations, four
   load zones, and 12 transmission connections.

The static network has 700 MW aggregate generation and 700 MW aggregate demand.
This balance is a deliberate interface fixture. It is not synchronized with the
historical series and does not establish feasible line flows or frequency stability.

## 3. Measurement validation method

The preprocessing pipeline retains only the canonical fields required by the
Phase 1 contract. It parses timestamps into UTC and converts measurement fields to
numeric values. A row is rejected when any of these conditions holds:

- a required column is absent;
- the timestamp is invalid, lacks an explicit UTC offset, or is not on an hourly
  boundary;
- one or more numerical values are non-finite;
- demand, solar generation, or wind generation is negative;
- frequency is outside 45–55 Hz, which is an ingestion sanity range rather than an
  operational threshold;
- the source label is missing; or
- the timestamp occurs more than once. Every member of a duplicate group is
  rejected to avoid arbitrary conflict resolution.

Accepted rows are sorted chronologically. The pipeline reports missing hourly
periods but performs no interpolation or imputation. It writes both a canonical CSV
and a JSON audit containing input, acceptance, rejection, reason, gap, timezone,
and cadence information.

## 4. Grid representation method

Grid assets are represented as a JSON document and validated into an undirected
NetworkX graph. Node categories are plant, substation, and load. Required numerical
properties depend on category: plants require capacity and output, substations
require voltage, and loads require demand. Edges require unique identifiers,
existing distinct endpoints, positive finite capacity, and a valid status.

The validator enforces unique node and edge identifiers, prevents duplicate edges,
rejects plant output above capacity, and requires the initial teaching topology to
be connected. This is a structural validation method. Stored source and target
fields do not assert a fixed direction of electrical flow.

The same document can be persisted to Neo4j. The import is namespaced by dataset,
replaces only that namespace in one transaction, and uses a composite uniqueness
constraint. Repeating the Phase 1 import therefore produces the same 12 nodes and
12 relationships rather than duplicates.

## 5. Dispatch baseline method

The deterministic baseline receives an aggregate observation:

- demand in MW;
- generation in MW;
- available controllable reserve in MW;
- battery state of charge as a fraction;
- forecast renewable trend as a fraction; and
- a Boolean observed-fault flag.

Inputs must be finite, nonnegative where applicable, and inside the declared state
ranges. The baseline calculates the aggregate power gap

\[
g = P_{demand} - P_{generation}.
\]

If \(|g| \leq 1\) MW, it recommends holding output. For a positive gap with reserve,
it requests \(\min(g, P_{reserve})\) MW of increased generation and reports any
remaining gap. With no reserve it identifies load shedding as a category but marks
the action infeasible. For a negative gap it recommends decreased generation but
does not claim feasibility.

Every returned recommendation has `executable: false`. Phase 1 checks aggregate
reserve only; it does not check ramp limits, minimum generation, battery energy,
load eligibility, transmission congestion, or power flow.

## 6. Q-learning interface design

Phase 1 implements the encoding function but does not train a Q-table. The proposed
state is the Cartesian product of:

- five supply-demand-gap bins;
- three renewable-trend bins;
- three battery-state-of-charge bins;
- three controllable-reserve bins; and
- two fault states.

This produces \(5 \times 3 \times 3 \times 3 \times 2 = 270\) discrete states.
The action vocabulary contains hold, increase generation, decrease generation,
charge battery, discharge battery, and shed load, yielding 1,620 possible
state-action values.

The environment owns an isolated copy of the topology and implements `reset()`.
The `step()` method deliberately raises `NotImplementedError`; transitions, rewards,
episode termination, and training are Phase 2 work. The proposed reward and update
rules are documented in `docs/dispatch_rl_design.md` and remain unmeasured.

## 7. API and interface method

Flask exposes health, module status, topology, measurements, quality audit, baseline
dispatch, and OpenAPI endpoints. Forecast, learned dispatch, explanation, and
scenario endpoints return HTTP 501 in Phase 1. This makes missing capability
observable and prevents placeholder data from being mistaken for model output.

The dashboard renders API-derived totals, topology, asset details, and measurement
charts. It includes asset-type filtering, 24-hour and 7-day sample ranges, light and
dark themes, and responsive navigation. The interface labels all displayed data as
synthetic and states that line flow and fault propagation are not calculated.

## 8. Phase 1 verification method

Verification combines automated and integration checks:

- 19 unit and API tests cover data rejection, gap reporting, topology constraints,
  isolated environment reset, baseline behavior, state encoding, API validation,
  planned HTTP 501 responses, and missing-fixture handling;
- JavaScript syntax is checked with Node;
- a disposable Neo4j 5.26 Community container verifies two consecutive imports;
- desktop and mobile browser checks cover data loading, asset selection, responsive
  containment, theme/sidebar persistence, filtering, chart ranges, and console
  errors.

These checks establish implementation consistency. They do not establish external
validity, forecasting performance, dispatch quality, causal accuracy, or safety.

## 9. Threats to validity

Phase 1 uses a fictional topology and two weeks of generated observations. The
fixtures omit real measurement noise, seasonality, weather, market behavior,
electrical impedances, voltage, reactive power, protection behavior, and operator
decisions. Consequently, no numerical Phase 1 result can be generalized to Delhi
or the Indian grid. Later experiments must retain this distinction and compare
methods using audited real or explicitly synthetic datasets.

## 10. Phase 2 implementation checkpoint: 2026-09-26

Phase 2 extends rather than replaces the Phase 1 methods above. The first
implementation checkpoint adds three executable research components.

### 10.1 Scenario construction

The adapter in `prism/simulation/scenario.py` selects up to 24 hourly validated
observations and linearly interpolates demand, solar, and wind at quarter-hour
boundaries. The final hourly value is held for its remaining three quarter-hours.
This interpolation creates a simulation profile; it does not modify or impute the
canonical measurement dataset.

### 10.2 Aggregate simulator

`GridEnvironment.step()` now returns `(observation, reward, terminated, info)`.
The default episode contains 96 fifteen-minute steps and uses a 25 MW action
quantum. Synthetic configuration assumptions are:

| Parameter | Current value |
|---|---:|
| Battery energy capacity | 100 MWh |
| Battery power limit | 50 MW |
| Initial battery state of charge | 0.50 |
| Charge/discharge efficiency | 0.95 |
| Coal ramp per step | 20 MW |
| Gas ramp per step | 40 MW |
| Coal minimum output | 40% of capacity |
| Gas minimum output | 20% of capacity |

Generator commands are clipped by ramp, capacity, and minimum-output constraints.
Battery commands are clipped by power, energy, and efficiency constraints. Load
shedding uses non-critical loads only. Scheduled node or line outages change asset
availability for a declared number of steps; NetworkX reachability identifies load
with no path to an online plant.

The reward records unserved energy, surplus energy treated as curtailment,
synthetic operating cost, and synthetic emissions. It heavily penalizes unserved
energy and any unexpected constraint violation. The cost and emission factors are
simulation assumptions, not observed plant data. The model does not calculate
voltage, reactive power, frequency dynamics, line loading, or feasible electrical
power flow.

### 10.3 Tabular Q-learning

The Q-learning implementation uses the Phase 1 270-state encoding and six-action
vocabulary. Exploration and greedy selection are restricted to the environment's
current valid actions. Terminal transitions do not bootstrap. The default training
configuration uses 500 episodes, learning rate 0.1, discount 0.99, and linear
epsilon decay from 1.0 to 0.05.

`scripts/train_q_learning.py` trains outside the web request path. The saved JSON
contains the state shape, action order, training configuration, metadata, and 270 ×
6 Q-values. Loading rejects incompatible action orders, state shapes, and non-finite
tables. A trained artifact is not yet configured as the application dispatch
policy; multi-seed comparison against the baseline remains required.

### 10.4 Forecasting baselines

Persistence repeats the most recent value. The autoregressive baseline fits a
ridge-regularized univariate linear model to the previous 24 hourly values and
generates recursive forecasts. `scripts/evaluate_forecasting.py` reserves the final
48 observations as a chronological test period and reports MAE and RMSE for demand,
solar, and wind. This is a pipeline check on synthetic data, not a claim of expected
performance on real measurements.

### 10.5 Phase 2 API boundary

`GET /api/forecast` exposes the two development forecasting methods for horizons
from one to 24 hours. `POST /api/scenario` runs one to 96 synthetic steps with a
fixed seed, optional scheduled faults, and either one supplied action per step or
the rule-based prototype. The response includes every transition and cumulative
metrics. Learned dispatch and explanation endpoints continue to return HTTP 501
until reviewed artifacts are configured.
