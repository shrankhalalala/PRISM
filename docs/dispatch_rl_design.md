# Dispatch, Q-learning and explainability — Himangi Mishra

## Phase 1 implementation

`Observation`, `Action`, `encode_state` and `recommend` are working contracts.
There is no trained Q-table, XGBoost model or SHAP explanation yet. Baseline
recommendations are non-executable aggregate suggestions. `feasible` refers only
to the aggregate reserve check, not electrical feasibility.

The initial action is an aggregate category. Phase 2 translates an action into
asset-level commands subject to availability, minimum output, MW ramp per step,
battery charge/discharge power, energy in MWh, efficiency and eligible load.
Renewables cannot be increased beyond available power. Decrease and shedding
remain unchecked in the prototype. Frequency is not inferred from power balance.

## State encoding

| Dimension | Bins (boundary equality is intentional) |
|---|---|
| Gap = (demand − generation) / max(demand,1 MW) | ≤−0.10; (−0.10,−0.02]; (−0.02,0.02]; (0.02,0.10]; >0.10 |
| Forecast renewable trend, fraction | <−0.05; [−0.05,0.05]; >0.05 |
| Battery SOC, fraction | <0.20; [0.20,0.80]; >0.80 |
| Controllable reserve / max(demand,1 MW) | <0.05; [0.05,0.20]; >0.20 |
| Observed fault flag | false; true |

270 states × 6 actions = 1,620 Q-values. This compressed state is an approximation
and may alias physically different grid situations. Compare failures by topology
and consider a revised representation if policy quality suffers.

Actions: hold, increase_generation, decrease_generation, charge_battery,
discharge_battery, shed_load. Proposed initial command quantum: 25 MW per
15-minute step, clipped by the shared constraint layer. HOLD remains valid;
invalid commands are masked during exploration, greedy selection and bootstrap
maximization. A diagnostic no-feasible-correction condition should be explicit.

## Episodes and reward specification (to implement in Phase 2)

An episode is 96 fifteen-minute steps. The data adapter must explicitly document
any profile interpolation from hourly input. Seed scenario generation and random
exploration independently. Initial battery capacity 100 MWh, SOC 0.5, power cap
50 MW, charge/discharge efficiency 0.95 are synthetic configuration assumptions.

Proposed normalized step reward:
`r = -(10 * unserved_MWh / demand_reference_MWh
       + 1 * operating_cost / cost_reference
       + 0.5 * emissions_kg / emissions_reference
       + 20 * violation_indicator)`.

Reference quantities must be positive, fixed from training configuration, and
saved with the policy. Use MWh = MW × step_hours. Do not reward a policy merely
for selecting an action or avoiding demand accounting. Count served energy,
curtailment, battery losses, and load shedding consistently. Penalties diagnose
unexpected violations; the feasibility layer should prevent invalid actions.
Weights are provisional; report sensitivity and competing objectives separately.

Proposed tabular update:
`Q(s,a) += alpha * (r + gamma * max_valid Q(s_next,a_next) - Q(s,a))`.
Use terminal target `r` without bootstrapping. Starting experiment: alpha=0.1,
gamma=0.99, epsilon from 1.0 to 0.05; tune only on validation scenarios. Episode
ends at the horizon; any early termination must account for remaining unserved
energy so termination cannot improve reward artificially.

## XGBoost and SHAP integration

Q-learning owns the learned dispatch policy. Train XGBoost on state/action records
from the frozen learned policy using independent episode-level splits. It is a
surrogate, not an independent proof of dispatch optimality. Report agreement,
per-action precision/recall, rare-fault performance and actual operating outcomes.
SHAP explains the surrogate's class score, not the Q-table or physical causality.
Show the Q-learning action, surrogate action, disagreement and any feasibility
override separately. Never present a surrogate explanation for a different action.

Evaluation: use identical unseen profiles and fault seeds for rule-based and
learned policies; report unserved energy, costs, emissions, violations, returns,
and variability across training seeds. Synthetic performance is not real-grid
validation. All rewards and transitions remain Phase 2 work.
