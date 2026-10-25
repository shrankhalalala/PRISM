# PRISM: Power Grid Resilience through Intelligent Smart Management

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask 3.1](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![NumPy 2.2](https://img.shields.io/badge/NumPy-2.2-013243?logo=numpy&logoColor=white)](https://numpy.org/)
[![pandas 2.2](https://img.shields.io/badge/pandas-2.2-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![NetworkX 3.3](https://img.shields.io/badge/NetworkX-3.3-2C5BB4)](https://networkx.org/)
[![Neo4j 5.26](https://img.shields.io/badge/Neo4j-5.26-4581C3?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![HTML5, CSS3, JavaScript](https://img.shields.io/badge/Frontend-HTML5%20%7C%20CSS3%20%7C%20JavaScript-E34F26?logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web)

PRISM is an academic decision-support prototype for studying resilient power-grid
operation under changing demand, renewable generation, and equipment faults. The
intended system combines time-series forecasting, constraint-aware dispatch,
Q-learning, explainable machine learning, and graph-based fault diagnosis in one
operator-facing workflow.

Phase 3 integrates a source-qualified Delhi reference graph, public live aggregate
and station measurements, durable Redis/PostgreSQL ingestion, audited real demand
forecasts, a six-action policy surrogate, actual TreeSHAP, graph investigation,
recoverable background jobs and an advisory operator workflow.

**Current status:** integration milestones are implemented. The reference inventory
contains 66 assets and 50 qualifying Delhi identities; 49 source stations have exact
telemetry mappings. The two-year requested demand range retains its missing data.
The validated local deployment runs at `http://127.0.0.1:5053/`.

**Research boundary:** reference evidence is not a complete electrical operating
model. Scenarios and dispatch policy remain synthetic; real solar/wind history,
physical frequency/cascade validation, qualified operator surveys and long-term
availability are outstanding. LSTM accuracy and learned-policy cost targets are
not met. All recommendations remain non-executable. Phase 2 artifacts and negative
comparisons remain intact.

Read [the current completion and target register](docs/PHASE3_COMPLETION.md),
[deployment instructions](docs/PHASE3_DEPLOYMENT.md), and
[demo guide](docs/PHASE3_DEMO.md). The editable demo deck is
[PRISM_Phase 3_Demo.pptx](deliverables/PRISM_Phase 3_Demo.pptx).

## Technology stack

| Technology | Role in PRISM |
|---|---|
| [Python](https://www.python.org/) | Application, simulation, forecasting, Q-learning, scripts, and tests |
| [Flask](https://flask.palletsprojects.com/) | Local web application and JSON API |
| [NumPy](https://numpy.org/) | Numerical operations, Q-table storage, metrics, and the compact LSTM |
| [pandas](https://pandas.pydata.org/) | Measurement validation, chronological datasets, and scenario profiles |
| [NetworkX](https://networkx.org/) | Topology validation, connectivity, and fault reachability |
| [Neo4j](https://neo4j.com/) | Immutable reference evidence and verified diagnostic input |
| Redis / PostgreSQL / Celery | Durable streaming/history and recoverable background lifecycle |
| XGBoost / SHAP | Six-action Q-policy surrogate and actual score attribution |
| [HTML, CSS, and JavaScript](https://developer.mozilla.org/en-US/docs/Web) | Responsive dashboard, charts, themes, and interactions |
| [Docker Compose](https://docs.docker.com/compose/) | Seven-service local deployment |

## Research motivation

Increasing renewable penetration makes grid balancing more dependent on timely
forecasts, rapid diagnosis, and dispatch decisions that operators can understand.
PRISM investigates whether a digital-twin-style environment can connect these
functions while keeping the recommendation process observable and reproducible.

The project is guided by four questions:

1. How accurately can demand and renewable generation be forecast at a useful
   operational horizon?
2. Can a Q-learning policy improve simulated dispatch outcomes relative to a
   deterministic baseline while respecting shared feasibility constraints?
3. Can an explainable surrogate reproduce the learned policy closely enough to
   provide useful local explanations without misrepresenting the policy?
4. Can graph topology, observed events, and event timing identify likely fault
   origins quickly and consistently in controlled scenarios?

Phase 1 does not answer these questions. It defines the interfaces and evidence
needed to test them in subsequent phases.

## Phase 1 contributions

| Area | Implemented contribution |
|---|---|
| Data | Strict hourly schema, validation, rejection audit, gap reporting, reproducible 336-row synthetic fixture |
| Grid model | Validated 12-node, 12-edge teaching topology using NetworkX, plus optional idempotent Neo4j persistence |
| Dispatch and RL | Validated observation contract, six-action vocabulary, 270-state encoding, and non-executable aggregate baseline recommendation |
| Simulation | Isolated resettable environment skeleton; dynamics are deliberately unimplemented |
| Application | Flask API, OpenAPI document, responsive dashboard, asset inspection, filters, sample charts, and explicit planned-endpoint responses |
| Verification | 19 automated tests, JavaScript syntax check, live Neo4j import test, and desktop/mobile dashboard checks |

## Phase 2 contributions

| Area | Implemented contribution |
|---|---|
| Data and forecasting | 2,160-row audited synthetic fixture; persistence, autoregressive, and NumPy LSTM models; chronological comparison |
| Dispatch and RL | Five-seed tabular Q-learning evaluation, validation-selected JSON policy, non-executable recommendation API |
| Simulation | Constrained 15-minute transitions and a versioned five-scenario normal/ramp/fault suite |
| Application | Forecast and scenario APIs plus responsive labs, fault controls, charts, metrics, and event log |
| Evidence | Committed checksummed reports, reviewed artifacts, 42 automated tests, and desktop/mobile browser verification |

## System overview

```mermaid
flowchart LR
    A[Synthetic or future public data] --> B[Validation and quality audit]
    B --> C[Canonical measurements]
    D[Grid JSON] --> E[NetworkX topology]
    D --> F[Optional Neo4j store]
    E --> G[Environment observation]
    G --> H[Baseline and trainable Q-learning policy]
    C --> I[Flask API]
    E --> I
    H --> I
    I --> J[Operator dashboard]
```

The dashboard reads validated JSON/CSV fixtures and reviewed local model artifacts.
Neo4j is an optional persistence target and is not required to run the dashboard.

## Documentation

The five primary, human-readable research documents are:

- [`README.md`](README.md): project entry point, status, setup, and navigation.
- [`DECISIONS.md`](DECISIONS.md): accepted technical and research decisions.
- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md): implemented Phase 1–2 methods and
  their assurance boundaries.
- [`docs/DATASET_AND_PREPROCESSING.md`](docs/DATASET_AND_PREPROCESSING.md): data
  provenance, schema, validation, and limitations.
- [`docs/EXPERIMENTAL_PROTOCOL.md`](docs/EXPERIMENTAL_PROTOCOL.md): construction
  criteria, evaluation rules, and the Phase 2 result record.

Supporting specifications remain in `docs/architecture.md`,
`docs/dispatch_rl_design.md`, `docs/openapi.json`, and `docs/verification.md`.
The Review II-IV Phase 3 checklist, gaps, evaluation targets, and ordered
completion gates are in [`docs/PHASE3_REQUIREMENTS.md`](docs/PHASE3_REQUIREMENTS.md).
The Delhi 400/220 kV boundary, source dates, inclusion rules, and acquisition
gaps are specified in [`docs/DELHI_TOPOLOGY_SCOPE.md`](docs/DELHI_TOPOLOGY_SCOPE.md).
The dated acquisition manifest, source locators, access gaps and local-archive
verification commands are in [`data/sources/delhi/README.md`](data/sources/delhi/README.md).
The source-referenced node inventory, coverage counts and open identity issues
are in [`data/topology/delhi/README.md`](data/topology/delhi/README.md).
The dated circuit inventory and Steps 5–6 completeness findings are in
[`data/topology/delhi/AUDIT.md`](data/topology/delhi/AUDIT.md). The audit currently
holds electrical/model integration pending unresolved topology evidence.
All phase-wise individual work is recorded in the single root-level
[`CONTRIBUTIONS.md`](CONTRIBUTIONS.md).

For installation, platform-specific commands, verification, and troubleshooting,
see [`INSTRUCTIONS.md`](INSTRUCTIONS.md).

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

Reproduce the Phase 2 experiments and committed review artifacts:

```bash
python -m scripts.evaluate_forecasting
python -m scripts.evaluate_q_learning --episodes 500
```

These commands write inspectable reports in `reports/` and reviewed JSON models in
`models/`. The reports retain data/model checksums, chronological splits, five
independent Q-learning seeds, and paired held-out scenario metrics.

Generated data: `data/raw/grid.json`, `data/raw/synthetic_measurements.csv`.
Prepared data and audit: `data/processed/`. The 90-day generated sample supports
method comparison, not claims about real-grid or seasonal accuracy. It is separate from the
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
| GET /api/measurements?limit=24 | Latest sample rows; limit 1–2160 |
| GET /api/data/quality | Preprocessing audit |
| GET /api/live/gridwatch | Latest Delhi SLDC public reading with source timestamp, freshness, and 60-second process cache; 503 if no valid reading exists |
| GET or POST /api/dispatch/baseline | Non-executable baseline preview |
| GET /api/openapi.json | OpenAPI contract |
| GET /api/forecast?target=demand_mw&model=lstm&horizon=1 | Synthetic persistence, autoregressive, or LSTM forecast; horizon 1–24 |
| POST /api/scenario | Run 1–96 constrained synthetic steps with baseline/Q-learning policy, optional actions, and faults |
| POST /api/dispatch | Reviewed Q-learning recommendation; always `executable: false` |
| POST /api/explain | 501 until the Phase 3 explanation model is configured |

Example POST body for `/api/dispatch/baseline`:

```json
{"demand_mw": 900, "generation_mw": 700, "reserve_mw": 50}
```

The proposal is 50 MW increased generation with 150 MW residual gap and
`executable: false`. Feasibility describes aggregate reserve only; plant ramp,
minimum output, battery, and topology availability checks are applied only inside
the Phase 2 scenario simulator.

Example scenario request:

```json
{
  "steps": 4,
  "seed": 42,
  "faults": [{"step": 1, "asset_id": "gas", "duration_steps": 2}]
}
```

If `actions` is omitted, set `policy` to `baseline` or `q_learning`; both share the
simulator's action mask. Supplying `actions` requires one of the six documented
actions for every step and cannot be combined with `policy`.

## Project status and next phase

See `CONTRIBUTIONS.md` for the four members' phase-wise work and review
demonstrations. See `docs/architecture.md` for implementation boundaries,
`docs/dispatch_rl_design.md` for the detailed RL contract, and
`docs/dashboard.md` for interface behavior.

Phase 2 remains the frozen synthetic baseline. Phase 3 now implements the
integration workflows and records evidence for each report target. Phase 4 research
acceptance still requires the field/data/operator validation listed in the
completion register; implementation alone does not establish those results.

## Verification environment

The local Python 3.12 suite passes 111 tests. The complete Linux container stack was
built from constrained dependencies and exercised through actual HTTP/worker/
Redis/PostgreSQL/Neo4j paths. Desktop/mobile and independent interface review pass.
`requirements-tested.txt` retains the historical Phase 2 environment;
`requirements-phase3-tested.txt` records current constrained versions.
See [verification](docs/verification.md) and the current report register for scope.

## Delhi reference dataset

The [Step 7 reference import guide](docs/DELHI_REFERENCE_IMPORT.md) describes
source-supported reconciliation and the independent, versioned Neo4j dataset.
Validate/export with `python -m scripts.import_delhi_reference`; import with
`--import-neo4j` after configuring the optional driver and credentials. This
reference dataset retains unknown fields and unresolved terminal details and is
visible in its own website view, separate from synthetic simulation. The electrical-completeness gate remains
open. Non-secret local import evidence is in `reports/phase3_reference_import.json`.
