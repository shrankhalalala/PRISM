# Background jobs and advisory decisions

Load the ignored environment, initialize `python -c 'from prism.operations.store
import initialize; initialize()'`, then start:

```
celery -A prism.operations.tasks:celery worker --pool=solo --concurrency=1
celery -A prism.operations.tasks:celery beat --schedule artifacts/celerybeat-schedule
```

PostgreSQL jobs are committed before publication (durable outbox). The 30-second
recovery task republishes queued jobs; atomic claims prevent duplicate execution.
An optional Idempotency-Key returns the same job for the same request and rejects
conflicting reuse. Worker messages are late-acknowledged with a bounded 10-minute
time limit. Running jobs with expired ten-minute leases are recovered; at most
three attempts are permitted. Transient failures return to queued; invalid inputs
fail. Broker failures retain queued work. Recovery requires a live beat/worker.
Scenario runs are bounded to 96 steps and share the synchronous preview runner;
cancellation is checked every four steps. Cancelled jobs cannot be overwritten
by late completion. No arbitrary code or file path is accepted as job input.

The hourly job requests three recent public Delhi demand days, at one request per
second or slower. It preserves checksummed recent originals under ignored
artifacts, stores quality-preserving hourly means in PostgreSQL, and updates a
separate recent context CSV atomically. The frozen training/audit dataset remains
unchanged. Forecast cache keys include the recent context hash, while models
retain their training-data hashes. Forecasts require 24 consecutive eligible input
hours. Failed refreshes keep prior context and explicit source age; they do not
pretend to produce current data. Retraining is a separate lifecycle.

The Operations page provides service health, application/data-quality alerts,
scenario jobs, actual surrogate TreeSHAP and human decision records. Alerts concern
stale/unavailable data, mapping issues or failed jobs; unknown electrical limits
cannot support overload/fault assertions. Health identifies Redis/PostgreSQL/worker
separately. A heartbeat expires after two minutes; this is current service state,
not a long-term availability percentage.

Advisories retain exact supplied observations/masks, Q and surrogate actions,
model/background hashes and explanations. Accept/override requires an explicit
human click, operator label and reason; override stays within the recorded mask.
Decisions append records and never edit the advisory or send equipment commands.
Operator labels are supplied assertions, not verified organizational identities.
Application append-only storage is not a tamper-proof external audit service.
Software verification records are explicitly labeled and are not operator surveys.

Writes require X-PRISM-Operator-Token if PRISM_OPERATOR_TOKEN is configured. Without
a token, only loopback requests may write when PRISM_ALLOW_LOCAL_OPERATOR=1.
Deployment sets that flag to 0 and requires a secret token. The UI keeps any token
in memory only. Do not expose the local preview or broker/database ports publicly;
production organization authentication/TLS can be added at the reverse proxy.

Run `python -m scripts.verify_operations` against a configured local worker for
job completion, duplicate, cancellation, authorization and audit evidence. This
creates clearly labeled synthetic software-verification decisions, never physical
or real operator acceptance. Current evidence is in reports/phase3_operations.json.
