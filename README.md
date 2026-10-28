# PRISM — Power Grid Resilience through Intelligent Smart Management

Academic smart-grid research and decision support for Delhi: published readings,
reference-network evidence, demand forecasting, hypothetical outages, synthetic
policy analysis and explainable investigation.

**Phase 3 integration is implemented; research acceptance remains partial.**
See [all phases and acceptance targets](docs/PHASES.md) and
[team responsibilities](CONTRIBUTIONS.md).

## Run

Install/start Docker with Compose, then run from this directory:

```sh
cp .env.example .env
# Set NEO4J_PASSWORD, POSTGRES_PASSWORD and PRISM_OPERATOR_TOKEN in .env.
make up
```

Open **[localhost:5050](http://127.0.0.1:5050)**. Keep existing database passwords
when reusing volumes. This single Docker web endpoint connects to PostgreSQL,
Redis, Neo4j, the collector, worker and scheduler; do not start a second Flask server.

```sh
make status       # Service health and ports
make logs         # Web, worker and collector logs
make restart      # Rebuild web after frontend-only changes
make up           # Rebuild/start the complete stack after shared-code changes
make stop         # Stop, preserving data
make down         # Remove containers/network, preserving named volumes
```

Never use `down -v` for routine cleanup. [INSTRUCTIONS.md](INSTRUCTIONS.md) covers
credentials, service ports, commands without Make, deployment and troubleshooting.

## Phase 3 capabilities

| Workspace / service | Implemented scope |
|---|---|
| Network evidence | 66 assets, 245 dated circuit records and 16 interface assertions; search, filters, provenance, 49 mapped station readings and geographic asset inspection. |
| Geographic map | 49 sourced site locations; 17 unlocated assets remain in the directory. Geographic and telemetry coverage are distinct. |
| Demand outlook | Real Delhi demand, 24-hour forecasts, model selection, origin/freshness and empirical prediction intervals. |
| Simulation | Backend-streamed connectivity/outage scenarios with Run/Stop; separate synthetic aggregate lab with baseline/Q-learning policies. |
| Policy review | Synthetic observations, Q-policy advice, XGBoost surrogate, TreeSHAP, abstention and saved accept/override reviews. |
| Alarm investigation | Supplied timestamped alarms, ranked graph/timing hypotheses and evidence paths. |
| Models and operations | Synthetic history/experiments, durable jobs/cancellation, hourly demand refresh, weekly/drift candidate review and reversible model promotion. |

Background-job panels and queue controls are temporarily hidden at the user's
request; their backend APIs remain available. Protected actions use the top-bar
operator token, kept in browser memory. See the [dashboard guide and demo](docs/dashboard.md).

## Latest results and boundaries

The validation-selected direct autoregressive forecast reduced historical test
RMSE from **426.54 to 389.21 MW**. The residual LSTM improved **758.40 to 498.46 MW**
and meets the scoped peak-normalized MAE/RMSE targets. Original baselines remain
preserved; the improved bundle is registered with rollback. These are retrospective
results, not prospective validation. MAPE remains above 5%; nominal 90% intervals
covered 77.36% of held-out values.

Rechecking 190 incomplete demand days recovered no additional hours: **555 gaps
remain**. Real solar/wind history is unavailable. Six richer-state dispatch candidates
failed the validation reliability/cost gate and were not promoted.

Reference connectivity is not verified current electrical topology. Map segments
are endpoint relationships, not surveyed routes or measured flow. Station loading
is not plant output or capacity. Simulations do not validate power flow, protection,
frequency dynamics or switching; reviews never command equipment. Physical
validation, qualified operator studies and long-term deployment evaluation are
deferred. Full measurements and limits are in [PHASES.md](docs/PHASES.md).

## Development and checks

Flask/Gunicorn serves Jinja HTML, local CSS/fonts and JavaScript; there is no npm
frontend build. Leaflet is vendored with its licence; map tiles require internet.
NumPy/pandas, NetworkX, Neo4j, PostgreSQL/Redis/Celery and XGBoost/SHAP support the
research pipeline. See [architecture](docs/architecture.md) and [API schema](docs/openapi.json).

For host-side tests, use Python 3.11+:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-phase3-tested.txt
python -m pip install -e '.[phase3,neo4j]'
make test
```

Linux uses xgboost-cpu; macOS may need libomp. Docker remains the application entry
point. Latest executed suite: **126 tests passed**; dated checks are in
[verification.md](docs/verification.md). Read-only checks on port 5050:
`/api/health`, `/api/readiness`, `/api/operations/health`. Integration verifiers
submit jobs and may write/retrain; use them deliberately as documented in setup.

## Repository guide

| Location | Purpose |
|---|---|
| `prism/` | Backend, template, frontend and coordinate overlay |
| `data/` | Fixtures, reviewed inventories, manifests and local raw evidence |
| `models/`, `reports/` | Versioned models and measured evaluation evidence |
| `scripts/`, `tests/` | Acquisition, research, verification and tests |
| `docs/PHASES.md` | All phases, report traceability, targets and remaining work |
| `docs/` | Technical guides, methodology, provenance and verification |
| `deliverables/` | [Editable demo deck](deliverables/PRISM_Phase3_Demo.pptx); current metrics live in the phase register |
| `artifacts/` | Ignored runtime context/model history; preserve for reproducibility |

[DECISIONS.md](DECISIONS.md) records accepted design choices. Generated working
files are excluded from Git; raw evidence, models and persistent volumes must not
be treated as disposable caches.
