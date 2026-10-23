# PRISM Decision Record

This document records decisions that materially affect the scientific claims,
architecture, or reproducibility of PRISM. It is written for team members,
reviewers, and future authors of the project paper. A decision describes what was
chosen and why; it does not imply that all later implementation has been completed.

## Status vocabulary

- **Accepted:** used by the current implementation or approved design.
- **Proposed:** intended for a later phase and still open to evidence-based change.
- **Superseded:** retained for traceability but replaced by a later decision.

## ADR-001: Build a modular research prototype before model training

**Date:** 2026-09-12
**Status:** Accepted

### Context

Forecasting, reinforcement learning, graph diagnosis, and the dashboard depend on
shared definitions of measurements, grid assets, actions, and API payloads. Training
models before these contracts exist would make comparisons difficult to reproduce.

### Decision

Phase 1 implements the common data contracts, topology validator, environment
interface, deterministic baseline interface, API, dashboard, and verification
suite. Model training and dynamic simulation begin only after these boundaries are
testable.

### Consequences

- The repository is runnable before learned models are available.
- Planned model endpoints return HTTP 501 rather than fabricated predictions.
- Phase 1 demonstrates construction quality, not model accuracy.

## ADR-002: Use clearly labelled synthetic fixtures in Phase 1

**Date:** 2026-09-12
**Status:** Accepted

### Context

The proposed public sources differ in geography, sampling resolution, access
method, and completeness. Their suitability for hourly Delhi-level modelling has
not yet been established.

### Decision

Use deterministic synthetic measurements and a fictional Delhi-inspired teaching
network to validate software behavior. Preserve a `data_source` field and label the
dashboard as synthetic. Do not use the fixtures as evidence of real-grid accuracy.

### Consequences

- Any contributor can reproduce the initial dataset using seed 42.
- Tests do not depend on an external service.
- Real-data claims remain prohibited until provenance and coverage are audited.

## ADR-003: Reject questionable observations instead of silently repairing them

**Date:** 2026-09-12
**Status:** Accepted

### Context

Silent interpolation, timezone assumptions, or arbitrary duplicate selection can
hide data-quality problems and produce optimistic forecasting results.

### Decision

Require explicit timezone offsets and hourly timestamps. Reject all rows in a
duplicate timestamp group, non-finite values, negative power values, missing source
labels, off-hour timestamps, and frequencies outside the ingestion sanity range.
Report gaps without filling them.

### Consequences

- Preprocessing produces a machine-readable audit.
- Missing periods remain visible to later modelling stages.
- Imputation, if later required, must be a documented experimental decision.

## ADR-004: Separate topology representation from electrical simulation

**Date:** 2026-09-12
**Status:** Accepted

### Context

A connected graph supports asset relationships and tracing, but it does not by
itself calculate voltage, frequency, or feasible power flow.

### Decision

Use an undirected NetworkX graph for Phase 1 topology validation and Neo4j as an
optional persistence layer. Treat edge capacities as schema fields, not calculated
flows. Do not infer grid stability from aggregate generation-demand balance.

### Consequences

- The current graph can support interface and persistence tests.
- Future fault diagnosis must combine topology with observations and event timing.
- Dispatch claims require a later constraint layer and power-flow validation.

## ADR-005: Make Q-learning a core method and share its feasibility layer

**Date:** 2026-09-12
**Status:** Accepted for architecture; training is not implemented

### Context

The project requires reinforcement learning as a central contribution. Learned and
rule-based policies must be compared under the same constraints to avoid giving one
method an artificial advantage.

### Decision

Define a common `Observation` contract, six action categories, and a 270-state
tabular encoding in Phase 1. In later phases, apply the same asset-level feasibility
checks to rule-based, exploratory, greedy, and surrogate actions.

### Consequences

- Phase 1 can validate state encoding without claiming a trained policy.
- Action masking and constraint handling become part of the evaluation method.
- State aliasing is a known risk that must be examined experimentally.

## ADR-006: Explain a frozen Q-learning policy through an XGBoost surrogate

**Date:** 2026-09-12
**Status:** Proposed

### Context

TreeSHAP is well suited to tree models but does not directly explain a Q-table.
Operators need local explanations, while reviewers need clarity about what those
explanations represent.

### Decision

After Q-learning training, generate an independent state-action dataset from the
frozen policy and train XGBoost as a surrogate. Use SHAP to explain the surrogate's
class score. Display policy disagreement and feasibility overrides explicitly.

### Consequences

- SHAP explanations must never be described as direct explanations of Q-learning.
- Surrogate agreement, per-action errors, and operating outcomes must be reported.
- A surrogate explanation is invalid when it corresponds to a different action.

## ADR-007: Use Flask with browser-native frontend code for the first prototype

**Date:** 2026-09-12
**Status:** Accepted

### Context

The team needs a reproducible interface with minimal build tooling while backend,
simulation, and model contracts are still evolving.

### Decision

Use a Flask application factory and local HTML, CSS, and JavaScript. Keep the API
contract explicit through OpenAPI. Defer adoption of a larger frontend framework
until application complexity demonstrates a need.

### Consequences

- The dashboard runs after installing the Python project.
- There is no separate Node build process in Phase 1.
- Frontend migration remains possible without changing the API boundary.

## ADR-008: Separate planned targets from measured results

**Date:** 2026-09-12
**Status:** Accepted

### Context

The source design documents contain differing proposed targets, including forecast
MAPE thresholds. Presenting these values as achieved results would be misleading.

### Decision

Treat all numerical targets as provisional until one experimental protocol is
approved and the corresponding experiment is run. Store verified construction
evidence separately from future performance results.

### Consequences

- Phase 1 reports test outcomes and artifact counts only.
- No forecasting, diagnosis, dispatch, latency, or reliability target is claimed.
- Later changes to targets must be recorded here and in the experimental protocol.

## ADR-009: Use a deterministic aggregate simulator before adding power flow

**Date:** 2026-09-26
**Status:** Accepted

### Context

Q-learning needs repeatable transitions, rewards, action constraints, and fault
scenarios. The Phase 1 network does not include the impedance and electrical data
needed for a defensible AC or DC power-flow model.

### Decision

Implement a 15-minute aggregate teaching simulator with explicit synthetic
generator ramp limits, minimum outputs, battery limits, load-shedding eligibility,
and scheduled asset outages. Use NetworkX connectivity to identify disconnected
loads. Label every result as synthetic and state that no AC/DC flow is calculated.

### Consequences

- Baseline and learned policies can use the same transition and constraint layer.
- Scenarios are reproducible from their profile, fault list, configuration, and seed.
- Simulator outcomes cannot establish voltage, frequency, congestion, or real-grid
  security.

## ADR-010: Establish transparent forecasting baselines before LSTM training

**Date:** 2026-09-26
**Status:** Accepted

### Context

A learned forecasting model needs a reference that is easy to reproduce and audit.
The committed two-week synthetic fixture is too small to support a journal claim
about general forecasting performance.

### Decision

Implement persistence and ridge-regularized univariate autoregressive models first.
Evaluate them with chronological splits and MAE/RMSE. Treat their outputs as
development baselines; add an LSTM only after a larger audited dataset and fixed
train/validation/test periods are available.

### Consequences

- Forecast APIs and metrics can be tested without a GPU or heavy dependency.
- Any later LSTM must beat declared simple baselines on identical test windows.
- Current synthetic metrics remain engineering evidence rather than a research
  performance result.

## ADR-011: Persist Q-learning policies as reviewed JSON artifacts

**Date:** 2026-09-26
**Status:** Accepted

### Context

Training a Q-table inside an HTTP request would mix experimentation with serving
and make model provenance difficult to audit.

### Decision

Train through a separate command, save the action order, state shape,
hyperparameters, metadata, and all Q-values in a versioned JSON artifact, and
validate those fields during loading. Keep `/api/dispatch` unavailable until a
specific reviewed artifact is configured.

### Consequences

- Training is reproducible and policy files remain human-inspectable.
- The API cannot silently serve an unreviewed newly trained policy.
- Large experiment artifacts require an explicit retention and versioning policy
  before repeated studies begin.

## ADR-012: Use a compact NumPy LSTM for the Phase 2 comparison

**Date:** 2026-09-26
**Status:** Accepted

Phase 2 requires an LSTM comparison, while the reproducibility environment does
not include TensorFlow or PyTorch. Implement a single-layer univariate LSTM with
the standard four gates and clipped back-propagation through 24-hour windows in
NumPy. Fit normalization on training data only and save weights, configuration,
losses, provenance, and checksums as JSON. This keeps the path inspectable and
lightweight, although the autoregressive baseline currently performs better on all
three held-out synthetic targets.

## ADR-013: Freeze a five-scenario suite and retain negative policy results

**Date:** 2026-09-26
**Status:** Accepted

Version normal-day and renewable-ramp training scenarios, a plant-fault validation
scenario, and line-fault plus concurrent-fault test scenarios. Train five seeds,
select the served artifact only by validation return, and publish every paired test
metric. The selected policy is seed 23. It slightly lowers mean unserved energy but
has worse mean return, curtailment, cost, and emissions than the baseline, so the
API labels it non-executable and makes it an explicit user choice.

## ADR-014: Complete Phase 2 with synthetic evidence and defer live data

**Date:** 2026-09-26
**Status:** Accepted

Complete Phase 2 using a reproducible 90-day generated series and explicit
synthetic labels. Live or public-data ingestion begins in Phase 3 after source,
licence, cadence, and quality requirements are recorded. Phase 2 therefore remains
fully runnable without external services, but its results cannot support real-grid
accuracy or policy-superiority claims.

## ADR-015: Define a source-dated Delhi EHV reference boundary before graph expansion

**Date:** 2026-10-22
**Status:** Accepted for reference-data acquisition; actual inventory verification pending

### Context

Review III proposes at least 50 Delhi nodes and 500+ scalability; Review IV records
the existing 12-node teaching network and defers a larger real-data-based graph.
The public sources inspected have different dates and coverage, so replacing
the fixture with an allegedly current complete network would overstate evidence.

### Decision

Use the scope in `docs/DELHI_TOPOLOGY_SCOPE.md`: Delhi's 400/220 kV transmission
network with verified generation interfaces and immediate external supply
endpoints. Include relevant other-owner assets; do not recursively expand the
national network or model complete lower-voltage distribution feeders.

Add official DTL sources to the report's CEA/NPP candidates. Select the June 2019
existing-network material in DTL's October 2019 Rev-02 plan as a historical
connectivity anchor and separately reconcile the later station/circuit tables.
Planning symbols, webpage dates and aggregate live measurements do not establish
current asset status. Preserve provenance and unresolved differences.

### Consequences

- Count physical facilities separately from voltage/bus vertices and aliases.
  Track the 50-node goal without inventing assets; test 500+ scalability separately.
- The result is a source-dated reference graph until current coverage/status is
  verified. Owner, location, ratings, telemetry and simulation eligibility remain
  distinct properties; unknown values are not filled with fixture assumptions.
- Retain the reproducible synthetic dataset and its experimental results. Source
  acquisition, inventory, reconciliation, import and display remain separate gates.

## ADR-016: Import uncertain topology as immutable reference evidence

**Date:** 2026-10-22
**Status:** Accepted

### Context

The Step 6 audit found unresolved site, circuit-label and terminal coverage.
Additional DTL documents resolve SOW attribution and Timarpur nominal voltage,
but cannot certify a complete current operating graph. Implementation needs to
progress while preserving the report's evidence requirements and Phase 2 results.

### Decision

Add a separate reference schema and content-addressed Neo4j dataset. Store assets
and circuit observations as distinct entities with source endpoint references,
including unknowns and unresolved candidates. Preserve original extraction records
and apply source-qualified reconciliation as a separate review overlay. Do not
create simulation `LINE` relationships from dated observations.

Reference import can proceed with explicit unresolved evidence. Electrical/model
integration remains gated on completeness, site/terminal reconciliation and the
required operating parameters. No unknown rating, output or flow is filled from
the synthetic fixture. Repeated imports verify immutable contents and never
replace existing datasets. Exact persisted properties and endpoint references
must match the exported snapshot.

### Consequences

The database can support source/date inspection in Step 8 without implying a
verified operating network. The 50-node physical-site goal and 500+ scalability
target remain separately unverified. See `docs/DELHI_REFERENCE_IMPORT.md` for
reconciliation, schema, local setup and verification commands.

## ADR-017: Reconcile site identities and correct the report's node-count interpretation

**Date:** 2026-10-22
**Status:** Accepted

### Context

The reference import advanced before six identity/modeling discrepancies were
settled. Rechecking Review III physical pages 2 and 11 confirms a minimum of
50 Delhi substation/plant nodes, not 50 geographically separate sites. The earlier
extra site-count condition overstated the report's acceptance requirement.

### Decision

Apply source-hash-qualified identity review as a reproducible layer over immutable
source observations. Merge proven Dwarka, Wazirabad and 400 kV Ballabhgarh aliases;
keep BBMB 220 kV Ballabhgarh separate; retain Narela owner portions on an extended
bus; classify Budella by its dated planning status; record supported plant evacuation
interfaces and historical terminal details. Preserve original IDs and source values.

Count the 47 directory asset identities plus three identified Delhi plants for the
50-node reference coverage requirement. Exclude the extra BBMB Narela portion,
external assets, proposed Budella and aliases from that count. A plant and receiving
substation may be distinct electrical assets within one complex. Physical-site
counts remain separate. This corrects the stricter geographic-site interpretation
in earlier notes without implying a complete current operating network.

### Consequences

The six original node cases have dispositions at the declared reference abstraction.
Exact circuit suffixes, some terminal naming, source length conflicts and real operating
parameters remain explicit field limitations. Current switching completeness and
simulation readiness must not be inferred from node counts or reference connectivity.
The corrected immutable snapshot is imported twice and earlier database versions
are checked for preservation. See `data/topology/delhi/RECONCILIATION.md`.
