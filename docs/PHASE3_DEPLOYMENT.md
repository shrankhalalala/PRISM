# Phase 3 local deployment

The verified stack uses Gunicorn, Celery worker/beat, a dedicated collector,
Redis 7.4, PostgreSQL 17 and Neo4j 5.26 Community. Python dependencies are constrained
by requirements-phase3-tested.txt. Linux uses the official xgboost-cpu package;
macOS uses the regular CPU-capable wheel and needs libomp (Homebrew).

Create an ignored `.env` with strong generated NEO4J_PASSWORD, POSTGRES_PASSWORD
and PRISM_OPERATOR_TOKEN. For local host scripts also set PRISM_DATABASE_URL and
PRISM_REDIS_URL (localhost ports 5433/6380). Never rotate an existing database
password merely by editing Compose; preserve or deliberately migrate the volume.

```
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml build web
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml up -d neo4j redis postgres
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml run --rm initialize
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml up -d web worker beat collector
```

Open http://127.0.0.1:5053/. Production-style writes require the operator token;
enter it in the Operations page's password field, which keeps it in memory only.
This is a local deployment, not a public release. Database/broker/browser ports
bind to loopback. For a remote rollout, provide organization authentication, HTTPS,
backups and infrastructure monitoring appropriate to that environment.

`/api/readiness` checks reference data, PostgreSQL, Redis, Neo4j and model warmup.
TreeSHAP/model initialization completes before readiness to avoid a cold first
operator request; startup duration is reported separately. `/api/health` is process
liveness. Operations health separately reports current worker heartbeat. None of
these short checks establishes a 99.5% availability observation period.

Containers run as an unprivileged app user with a read-only root, writable artifact
volume and temporary /tmp. Seven services have explicit memory limits. Reference,
stream, database and model artifacts persist in distinct volumes. Redis AOF and
PostgreSQL commits support recovery; backups/restore drills remain deployment work.
The production queue prism-phase3-v3 prevents older preview workers from satisfying
production jobs. Do not run multiple beat instances against the same schedule.

Weekly candidate review runs Monday 02:00 UTC. A declared standardized mean-shift
proxy may queue at most one drift review per day after the hourly demand refresh.
Candidates train with chronological splits; validation chooses the model, and a
minimum 1% RMSE improvement on the same validation origins is required to promote.
At least ten validation origins are required. The reserved test period never
selects promotion. A failed gate retains the current bundle. A cancelled review cannot promote;
retraining cancellation closes once the atomic promotion stage reaches 90% progress,
so a late cancel request returns the still-running/terminal state instead. Versioned files are
fingerprinted, promotion uses an atomic pointer and a lock, and logs append under
artifacts/model-registry. The reviewed baseline is registered first so the first
promotion can roll back. POST /api/models/rollback (empty JSON, operator token)
restores the previous registered bundle. The mechanics are tested with labeled
fixtures; the real candidate did not improve and was correctly rejected.

Read `/api/models/status` for drift/version state. This is demand forecasting
lifecycle only; real dispatch/solar/wind retraining remains ineligible without
source history and validated dynamics. The drift proxy is season sensitive and
is not a measurement of model error drift.

Verify with `python -m scripts.verify_deployment` after loading the ignored host
environment, then `python -m scripts.measure_deployment_resources` on macOS/Docker.
The latter records actual container cgroup peaks and the host's observed 8 GB RAM;
the report's 16 GB feasibility assumption is not substituted for that measurement.

Stop with the same Compose files and `down`. Do not use `down -v` unless deliberately
discarding data. Export/back up PostgreSQL, Neo4j and artifact volumes separately.
The committed historical manifests require reacquiring raw originals for source
re-audits; the frozen hourly dataset is available immediately for the demo.

Licensing: no paid cloud/model/data service is required for this local setup.
Redis 7.4 uses RSALv2/SSPLv1, not an OSI open-source license; see
[Redis's license mapping](https://redis.io/legal/licenses/). Neo4j Community, the
Python components and their transitive dependencies retain their own notices;
shipping this project does not relicense them. Linux CPU installation follows
[the official XGBoost guide](https://xgboost.readthedocs.io/en/stable/install.html).

If a dependency starts after the web process, model readiness retries initialization
on subsequent readiness probes, at most once every five seconds per process.
Concurrent probes share one initialization attempt. Failed initialization remains
HTTP 503 until it succeeds; exception details are not exposed. Start the complete
Compose stack above so the collector, worker and scheduler can resolve their
PostgreSQL/Redis/Neo4j services. Restarting the web service alone does not restore
missing dependencies.
