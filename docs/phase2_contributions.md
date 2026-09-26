# Phase 2 contribution ownership and evidence plan

This file assigns Phase 2 review responsibility across the four agreed project
roles. It records what each member should understand, verify, improve, and present.
The code was scaffolded with Codex assistance, so ownership means accountable
review and contribution; it must not be represented as unaided individual
authorship.

## Checkpoint 1: executable simulation and learning backbone

| Owner | Current contribution area | Artifacts to review and extend | Individual review demonstration |
|---|---|---|---|
| Nishtha Jain (22803007) | Forecasting data and benchmarks | `prism/forecasting/`; `prism/simulation/scenario.py`; `scripts/evaluate_forecasting.py`; dataset documentation | Explain the chronological split and quarter-hour adapter; run both forecasting baselines; interpret MAE/RMSE without treating synthetic metrics as real-grid accuracy |
| Himangi Mishra (22803016) | Constrained dispatch and Q-learning | `prism/dispatch/q_learning.py`; `prism/dispatch/baseline.py`; `scripts/train_q_learning.py`; `docs/dispatch_rl_design.md` | Explain action masking and the Q update; reproduce a seeded training run; load a saved Q-table; identify why policy comparison is still pending |
| Shrankhala Singh (22803022) | Grid dynamics and fault simulation | `prism/simulation/environment.py`; topology interactions; simulator tests; Phase 2 architecture | Demonstrate ramp and battery limits; inject and restore a plant or line outage; explain disconnected demand and the absence of electrical power flow |
| Gaurangi Tyagi (22803012) | API and application integration | `prism/__init__.py`; `docs/openapi.json`; API tests; forthcoming simulation dashboard | Call forecast and scenario endpoints; demonstrate input errors and synthetic-result labels; design the next dashboard controls without enabling an unreviewed policy |

## Shared checkpoint evidence

- All four members use the same six actions, 270-state encoding, scenario profile,
  fault schema, and metric definitions.
- The automated suite contains 37 passing tests at this checkpoint.
- Q-learning and forecast commands run independently of the Flask server.
- `/api/dispatch` and `/api/explain` remain unavailable until reviewed artifacts
  exist; no placeholder output is presented as a model result.
- Each member should contribute commits in their assigned area and retain command
  output or experiment artifacts that can be traced to those commits.

## Remaining Phase 2 allocation

| Owner | Next accountable deliverable | Completion evidence |
|---|---|---|
| Nishtha | Larger audited dataset and LSTM comparison | Frozen chronological splits, baseline/LSTM metrics, configuration, and model checksum |
| Himangi | Multi-seed Q-learning evaluation against the rule-based policy | Per-seed returns and operational metrics on identical held-out scenarios |
| Shrankhala | Scenario suite and simulator sensitivity review | Versioned normal, renewable-ramp, plant-fault, line-fault, and concurrent-fault definitions |
| Gaurangi | Simulation and forecast dashboard views | Accessible controls, trajectory/metric display, error states, responsive checks, and browser verification record |

Phase 2 should be marked complete only after all four deliverables have reviewable
evidence. A passing smoke run alone is not sufficient for a research conclusion.
