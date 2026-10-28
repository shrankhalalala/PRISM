# PRISM team responsibilities

This is the single team responsibility record across all phases. Assignments cover
understanding, reviewing, maintaining, testing and presenting the work. Repository
artifacts establish implementation status; they do not prove each member personally
authored or reviewed them. Individual claims require that member's commit/review or
experiment evidence. System status and metrics belong in [docs/PHASES.md](docs/PHASES.md).

## Team

| Member | University ID | Continuing responsibility |
|---|---|---|
| Nishtha Jain | 22803007 | Data engineering and forecasting |
| Himangi Mishra | 22803016 | Dispatch, Q-learning and explainability |
| Shrankhala Singh | 22803022 | Grid modelling, simulation and faults |
| Gaurangi Tyagi | 22803012 | API, dashboard and application integration |

## Phase 1 and Phase 2 scope

These summarize the established assignments without repeating checkpoint logs.

| Member | Phase 1 — foundation | Phase 2 — simulation and learning |
|---|---|---|
| Nishtha | Measurement schema, synthetic generator, preprocessing, data dictionary and sources | 2,160-hour fixture, chronological forecasting evaluation, persistence/AR/LSTM and model provenance |
| Himangi | Observation/action contracts, rule baseline and 270-state encoding | Masked six-action Q-learning, five training seeds, validation selection and paired policy comparison |
| Shrankhala | Grid validation, NetworkX/Neo4j and environment design | 15-minute transitions, generation/battery constraints, scheduled outages and five-scenario fault suite |
| Gaurangi | Flask/API contract, dashboard, inspection and charts | Forecast/scenario integration, policy/fault controls, results, responsive and error-state verification |

Historical evidence: [verification](docs/verification.md),
[forecast experiments](reports/phase2_forecasting.json),
[dispatch experiments](reports/phase2_dispatch.json), and
[scenario definitions](data/scenarios/phase2_scenarios.json).

## Phase 3 responsibilities and review evidence

| Member | Assigned Phase 3 scope | Evidence and individual demonstration |
|---|---|---|
| Nishtha | Source validation, timestamp/quality rules, station mapping provenance, durable history preparation, recovery, real-demand forecasts and retraining data eligibility | [History recovery](reports/phase3_history_recovery.json), [forecast refinement](reports/phase3_forecast_refinement.json), `prism/data/`, `prism/forecasting/`. Explain 555 remaining gaps, validation-only selection, residual LSTM/direct AR, uncertainty limits and unavailable renewable history. |
| Himangi | Frozen Q-policy, six-action surrogate, abstention, TreeSHAP and dispatch-refinement evaluation | [Surrogate](reports/phase3_surrogate.json), [SHAP fidelity](reports/phase3_shap_fidelity.json), [dispatch refinement](reports/phase3_dispatch_refinement.json), `prism/dispatch/`, `prism/explain/attribution.py`. Demonstrate action agreement/disagreement and explain why all six new candidates were rejected. |
| Shrankhala | Delhi scope/identity reconciliation, source-cohort and voltage-layer model, electrical eligibility, connectivity outages and graph investigation assumptions | [Reconciliation](data/topology/delhi/RECONCILIATION.md), [eligibility](reports/phase3_grid_eligibility.json), `prism/grid/`, `prism/simulation/`, `prism/explain/diagnosis.py`. Demonstrate an outage and explain missing buses/ratings, parallel evidence and the distinction between graph hypotheses and physical causality. |
| Gaurangi | API/UI integration, map inspection, freshness/errors, Docker services, worker/collector integration, protected reviews and model-registry lifecycle | [Operations evidence](reports/phase3_operations.json), [verification](docs/verification.md), `prism/operations/`, `prism/templates/`, `prism/static/`, Compose and Makefile. Demonstrate the single port-5050 stack, forecast provenance, cancellation, authorization and retained rollback. |

Nishtha owns source/model semantics; Gaurangi owns their service integration.
Himangi owns policy/attribution semantics; Shrankhala owns topology/fault semantics.
Cross-component tests are shared. These assignments do not assert completed
individual review or redistribute authorship based on generated implementation.

## Remaining responsibility

- **Nishtha:** eligible missing/renewable history, MAPE and interval-coverage improvement.
- **Himangi:** dispatch reliability/cost improvement before any policy or surrogate replacement.
- **Shrankhala:** independently sourced terminal, switching and electrical parameters;
  keep the 17 unlocated assets directory-only until coordinate evidence arrives.
- **Gaurangi:** preserve contracts, service recovery and reproducible deployment while
  integrating accepted changes; keep pending research limits visible.

Physical validation, qualified operator studies and long-term deployment evaluation
are deferred. No member is recorded as having completed those studies.
