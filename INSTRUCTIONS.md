# Run PRISM

The supported local application is the complete Docker stack, served at
[http://127.0.0.1:5050](http://127.0.0.1:5050). There is one web endpoint.
Ports 5433, 6380, 7474 and 7687 belong to its supporting services.

## First setup

1. Install and start Docker Desktop, or Docker Engine with Compose.
2. Open a terminal in the repository directory containing `compose.yaml`.
3. Copy `.env.example` to `.env` and replace the three secret placeholders:
   `NEO4J_PASSWORD`, `POSTGRES_PASSWORD`, `PRISM_OPERATOR_TOKEN`.
4. Run `make up`, then open port 5050.

Use existing database passwords when data volumes already exist. Changing a
password in `.env` does not migrate an existing database account.

On Windows or without `make`, run the equivalent commands in order:

```sh
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml build web
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml up -d postgres redis neo4j
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml run --rm initialize
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml up -d --no-build web worker beat collector
```

Always use the same project name and both Compose files. Starting another project
creates a second stack/volume set rather than repairing this one.

## Daily use

```sh
make status       # Service state and published ports
make logs         # Web, worker and collector logs; Ctrl+C exits log viewing
make restart      # Rebuild/recreate only web after template/CSS/JS changes
make stop         # Stop services; data remains
make up           # Start/rebuild and initialize idempotently
make down         # Remove containers and network; keep named volumes
```

Changes to shared backend/worker code require `make up`, so worker processes also
receive the updated image. `make restart` is appropriate for frontend-only changes.
Do not run a second `python -m prism` process or use old port 5053. Stop any stale
local preview before starting the Docker web container on port 5050.

Never use `docker compose down -v` for routine cleanup. It deletes database/artifact
volumes. Never open `prism/templates/index.html` directly; Flask must serve it.

## Service connections

| Service | Browser / host | Inside Docker |
|---|---|---|
| PRISM | `http://127.0.0.1:5050` | `web:5050` |
| PostgreSQL | `127.0.0.1:5433` | `postgres:5432` |
| Redis | `127.0.0.1:6380` | `redis:6379` |
| Neo4j Browser | `http://127.0.0.1:7474` | `neo4j:7474` |
| Neo4j Bolt | `bolt://127.0.0.1:7687` | `neo4j:7687` |

Compose reads `.env` and supplies the web/worker service URLs automatically.
Standalone Python does not auto-load `.env`, which is why the earlier direct Flask
preview reported unavailable services despite healthy Docker databases.

The top-bar Operator access field accepts `PRISM_OPERATOR_TOKEN` for protected
advisory/review mutations. It stays in browser memory. Do not paste secrets into
source files, reports, screenshots or recordings.

## Verify

Open `/api/health` for liveness, `/api/readiness` for configured dependencies, and
`/api/operations/health` for PostgreSQL/Redis/worker state on port 5050. These checks
describe application services, not electrical-grid health.

Run automated tests from a host research environment configured as in README:

```sh
make test
```

The optional `scripts.verify_deployment` integration script makes writes and queues
experiments and writes its report; it is not a read-only health check. It defaults
to port 5050; `PRISM_BASE_URL` overrides it for an intentionally different deployment.
Host scripts need exported service URLs and the operator token; Compose loads `.env`
only for its own services. `scripts.measure_deployment_resources` records actual
macOS/Docker workload measurements.

## Troubleshooting

| Symptom | Action |
|---|---|
| Port 5050 occupied | Inspect `lsof -nP -iTCP:5050 -sTCP:LISTEN` (macOS/Linux) or `netstat -ano` (Windows). Stop the identified stale PRISM preview; keep one Docker web endpoint. |
| Services unavailable | Use Docker's port 5050, run `make status`, then check `make logs`. Confirm `.env` and existing volume passwords match. |
| Reference/model error | Check readiness and logs. Preserve data/models; follow the relevant verification guide instead of regenerating them blindly. |
| Changes not visible | Run `make restart`, then hard-refresh the browser. |
| Map background missing | Street tiles require internet; sourced geographic pins and the directory remain usable. |
| Source readings stale/unavailable | Inspect the source timestamp and collector logs. Never substitute synthetic data for a failed public feed. |
| Worker startup fails | Check database/Redis health and the worker log with the same Compose project/files. |

Published readings, historical forecast previews, dated connectivity evidence and
synthetic research labs have different assurance boundaries. See the
[dashboard guide](docs/dashboard.md) and [phase and acceptance register](docs/PHASES.md).


## Deployment boundaries

The local stack uses Gunicorn, Celery worker/beat, a dedicated collector, Redis 7.4,
PostgreSQL 17 and Neo4j 5.26 Community. Dependencies are constrained by
`requirements-phase3-tested.txt`. The seven services have memory limits; application
containers run unprivileged with a read-only root, writable artifact volume and
`/tmp`. Redis AOF and PostgreSQL commits support recovery. Preserve the distinct
database, reference and artifact volumes; back them up separately.

Loopback-only ports and the operator token are local protections, not public-release
security. Docker disables anonymous local writes (`PRISM_ALLOW_LOCAL_OPERATOR=0`).
A remote rollout still needs organizational authentication, HTTPS, monitoring and
backup/restore drills. The `prism-phase3-v3` queue isolates production jobs from old
preview workers. Run only one scheduler and one collector for the same deployment.

Readiness includes reference data, dependencies and model/TreeSHAP warmup. A delayed
dependency triggers initialization retries on readiness probes at most every five
seconds per process; concurrent probes share an attempt. Failure remains HTTP 503
without exposing exception details. Operations health checks worker heartbeats
separately. Health checks do not establish 99.5% long-term availability.

## Forecast lifecycle

Hourly refresh retains source age on failure. Weekly review runs Monday 02:00 UTC;
a declared mean-shift proxy can request at most one drift review per day. Candidates
use chronological partitions and at least ten validation origins. Promotion needs
at least 1% RMSE improvement over the incumbent on the same validation origins;
test results do not select promotion. Model files are fingerprinted, pointer changes
are atomic/locked, and events append under `artifacts/model-registry`.

Failed gates retain the incumbent. Cancellation is honored before atomic promotion;
after 90% progress, late cancellation returns the running/terminal state. Read
`GET /api/models/status`; an intentional operator-authenticated
`POST /api/models/rollback` with `{}` restores the previous registered bundle.
The original candidate was rejected; the 2026-10-27 improved bundle was promoted.
These are demand-model mechanisms, not real dispatch or renewable retraining.

## Dependencies and source access

No paid cloud/model/data service is required locally. Redis 7.4 uses RSALv2/SSPLv1,
not an OSI open-source licence; see the [Redis licence mapping](https://redis.io/legal/licenses/).
Other components retain their notices. Linux uses xgboost-cpu; macOS may need
libomp. Frozen hourly data supports the demo without original raw downloads;
source re-audits require matching raw captures. Reacquisition access and reuse
conditions remain source-specific.
