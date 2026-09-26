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
