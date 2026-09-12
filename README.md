# PRISM — Phase 1

Power Grid Resilience through Intelligent Smart Management. A runnable academic
foundation for a four-person project, with Q-learning included in the core design.
**All bundled grid assets and measurements are synthetic.** No live grid feed,
trained policy, forecasting model, or operational switching is connected.

## Run locally

Requires Python 3.11+ (verified on Python 3.12). From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-tested.txt
python -m pip install -e .
python -m prism
```

Open http://127.0.0.1:5050 . Committed fixtures allow immediate startup. The Flask
server is a local development server. `PRISM_HOST` defaults to 127.0.0.1 and
`PRISM_PORT` to 5050. `.env.example` documents variables; export them in your shell
(the app does not automatically read .env).

## Reproduce sample data and run checks

```bash
python -m scripts.generate_sample
python -m scripts.prepare_data
python -m unittest discover -s tests -v
```

Generated data: `data/raw/grid.json`, `data/raw/synthetic_measurements.csv`.
Prepared data and audit: `data/processed/`. The 14-day sample supports pipeline
checks, not claims about seasonal forecasting accuracy. It is separate from the
static graph snapshot. See docs/data_dictionary.md for timestamps and rejection
rules, and docs/data_sources.md for real-data acquisition limitations.

## Optional Neo4j

The dashboard works without Neo4j. To verify the persistence adapter against a
local database, first install/start Docker, choose a local password and export it:

```bash
python -m pip install -e '.[neo4j]'
export NEO4J_PASSWORD='choose-a-local-password'
docker compose up -d neo4j
python -m scripts.seed_neo4j
```

Allow Neo4j to finish starting before seeding. Expected counts: 12 nodes, 12 edges.
Running the seed again replaces only the `prism_phase1` dataset; it does not append
copies. Browser UI: http://127.0.0.1:7474 . Query:

```cypher
MATCH (n:PrismNode {dataset: 'prism_phase1'}) RETURN n;
```

NetworkX/JSON validation is covered by automated checks. To run an isolated live
Neo4j import/idempotency test: `python -m scripts.verify_neo4j`. This downloads the
Community image, uses loopback port 17687, and removes its temporary container
afterward. A normal demo database is started separately using Compose above.

## API

| Route | Status |
|---|---|
| GET /api/health, /api/status | Application and module status |
| GET /api/grid | Validated grid with aggregate summary |
| GET /api/measurements?limit=24 | Latest sample rows; limit 1–336 |
| GET /api/data/quality | Preprocessing audit |
| GET or POST /api/dispatch/baseline | Non-executable baseline preview |
| GET /api/openapi.json | OpenAPI contract |
| GET /api/forecast | 501: planned |
| POST /api/dispatch, /api/explain, /api/scenario | 501: planned |

Example POST body for `/api/dispatch/baseline`:

```json
{"demand_mw": 900, "generation_mw": 700, "reserve_mw": 50}
```

The proposal is 50 MW increased generation with 150 MW residual gap and
`executable: false`. Feasibility describes aggregate reserve only; plant ramp,
minimum output, battery and network limits arrive with Phase 2 simulation.

## Team and next phase

See docs/phase1_contributions.md for the four owners and individual demonstrations.
See docs/architecture.md for boundaries, docs/dispatch_rl_design.md for the RL
contract, and docs/dashboard.md for the interface.

Phase 2 implements simulator dynamics and faults, baseline constraints, first
forecasting models, and Q-learning training. Phase 3 integrates streaming,
background simulation, XGBoost/SHAP and the full operator flow. Phase 4 evaluates
all modules and assembles final evidence. No accuracy or latency target is reported
as achieved by this foundation.

## Verification environment

The local `.venv` was created with access to existing system packages to reuse
available dependencies. Editable installation and all 19 tests passed there.
`requirements-tested.txt` records the core versions used; the commands above
create an isolated environment on a new machine. See docs/verification.md for
the final validation record. Restart the server after template changes when
running with debug mode disabled.
