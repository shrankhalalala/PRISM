# Redis and PostgreSQL ingestion

Install `pip install -e '.[phase3]'`. Set POSTGRES_PASSWORD in the ignored `.env`
and PRISM_DATABASE_URL / PRISM_REDIS_URL for local processes. Never commit secrets.
Start `docker compose -p prism-phase3-reference up -d redis postgres`.
Load the environment into the current shell, then run
`python -m scripts.collect_live --once` or omit `--once` for continuous collection.
Only one dedicated collector should poll upstream; it fetches each feed at most
once per minute. This is the observed integration cadence, not the report's
unverified six-second claim. The dashboard's direct adapter is a separate
per-process preview path until production service configuration is selected.

The collector validates finite source observations and timestamps, publishes
content-addressed events, and drains a Redis consumer group. Signed station MW
and MVAr are preserved. Event context distinguishes station loading from aggregate
measurements and retains source labels, RTU status and quality limitations.
A same-time corrected value creates another immutable revision. PostgreSQL retains
both; API queries order by observation time and stable event identity.

Redis atomically suppresses exact duplicate publications for 24 hours. The stream
is capped at 100,000 entries with backpressure rather than silent eviction.
AOF is enabled. The consumer writes PostgreSQL first, commits, then acknowledges.
After a crash, XAUTOCLAIM reclaims entries pending for at least 30 seconds.
PostgreSQL event_id uniqueness makes commit-before-ack replay idempotent. Malformed
messages go to a durable quarantine table before acknowledgement. Redis and DB
reconnect with bounded exponential delay; errors expose class names, not DSNs.

Time retention is one hour for acknowledged/delivered entries; unread and pending
entries remain protected even when older. One retained last-delivered entry may
remain beyond that window. Backlog health is degraded and the cap eventually
stops publication until recovery. Retention is not an arbitrary 86,400-entry
claim. Database history has no automatic deletion; capacity/backups need monitoring.

`GET /api/ingestion/health` returns queue/pending status or explicit unavailable.
`GET /api/history/<asset_id>?limit=100` exposes immutable records (limit 1–1000).
`python -m scripts.verify_streaming` verifies real infrastructure, duplicates,
commit-before-ack recovery, quarantine and retention protections.
`python -m scripts.benchmark_streaming` measures 200 **synthetic benchmark** events
without increasing SLDC polling. Local measurements do not establish deployment
availability or external source performance. Evidence is under `reports/phase3_*`.
