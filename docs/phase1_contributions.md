# Phase 1 contribution ownership and review checklist

These assignments map artifacts to the agreed team roles. The code was scaffolded
with Codex assistance; this table is an ownership/verification plan, not a claim
that individual students have already authored or reviewed each file.

| Owner | Artifacts | Individual review demonstration |
|---|---|---|
| Nishtha Jain (22803007) | prism/data/pipeline.py; scripts/generate_sample.py (measurements); scripts/prepare_data.py; docs/data_dictionary.md; docs/data_sources.md | Explain provenance; reject an invalid CSV row; inspect gaps and quality audit |
| Himangi Mishra (22803016) | prism/dispatch/baseline.py; docs/dispatch_rl_design.md; shared Observation/Action definitions | Explain 270 states, six actions and reward design; demonstrate reserve-limited recommendation |
| Shrankhala Singh (22803022) | prism/grid/*; prism/simulation/*; scripts/seed_neo4j.py; graph fixture; docs/architecture.md | Explain schema; validate connectivity; demonstrate isolated resets and optional Neo4j import |
| Gaurangi Tyagi (22803012) | prism/__init__.py; prism/templates/*; prism/static/*; docs/openapi.json; docs/dashboard.md | Run app; inspect API responses; select graph nodes; show error and planned-module states |

Each member should review and adapt their module, run its tests, maintain their
own commit history for subsequent work, and author their explanation/results.
Do not attribute generated scaffolding as independent manual work.

## Acceptance evidence

- Synthetic network: 12 nodes / 12 edges, 700 MW generation and demand.
- Synthetic history: 336 validated hourly rows, fixed seed 42.
- Baseline and state encoding run without trained model dependencies.
- Fault dynamics/model endpoints explicitly unavailable, never fabricated.
- Dashboard renders API values and supports refresh and node inspection.
- `python -m unittest discover -s tests -v` exercises validation and contracts.
- Neo4j live verification is separate from local graph validation; see README.
