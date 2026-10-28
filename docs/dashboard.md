# Dashboard guide

Start PRISM with `make up`, then open [localhost:5050](http://127.0.0.1:5050).
Do not run an additional standalone Flask server. See [setup](../INSTRUCTIONS.md)
for the Docker services and credentials.

## Navigation

The current workspace has Home, Network, Demand outlook, and Research destinations.
Research tabs select Simulation, Policy review, Alarm investigation, or Models/history.
Deep links open the relevant panel; legacy `#overview` / `#live-grid` lead to Home.
Desktop navigation can collapse to labelled-accessible icons. Phones use the existing
bottom navigation. Theme and desktop navigation preferences persist locally.

## Network evidence

- Search by asset name, ID or source alias, then apply the available type/boundary/
  classification/period filters. Reset restores the complete reference inventory.
- The geographic map plots 49 assets at sourced site coordinates. Seventeen assets
  without confirmed coordinates remain selectable in the asset directory.
- Drag or use arrow keys to pan; use scroll, +/− or the zoom buttons to zoom; use
  Home/Fit for all located matching assets. Selection preserves the current viewport.
- Asset and connection directories retain every backend record. The inspector
  shows mapped station measurements, source time, quality flags, original evidence
  references and available identity metadata. Location metadata names its source.
- Station loading is not generation, capacity, a line rating or electrical safety.
  Map segments are reference connections between endpoints, not measured power
  flows or surveyed physical routes.

## Demand outlook

The 24-hour system-demand forecast loads independently of station selection. Choose
validation-selected, LSTM, autoregressive or persistence models. Inspect the source
origin, historical-preview label, available empirical interval, hourly predictions
and model/data provenance. Nominal interval coverage is not guaranteed coverage.
Real solar/wind comparisons are unavailable; their teaching examples remain synthetic.
Failed refreshes retain any previous forecast with its original source time.

## Research

**Simulation:** choose up to 96 connectivity steps, backend pacing and up to eight
asset/connection disruptions, each with start/duration. Empty targets give a baseline.
Run consumes actual backend snapshots; Stop interrupts the stream and retains the
last received state. Logs and metrics come from the backend. This is hypothetical
connectivity research, without validated power flow, switching, dispatch or protection.
The Advanced aggregate lab retains its separate synthetic baseline/Q-learning model,
fixture faults, totals, trajectories and action/event log.

**Policy review:** edit the labelled synthetic observation and candidate actions.
Generate advice; inspect Q/surrogate agreement, abstention, score factors and provenance.
Accept/override records a human review with an operator label and reason; it sends
no equipment command. Operator access in the top bar accepts the configured token,
kept in page memory only.

**Alarm investigation:** supply timezone-qualified timestamps and eligible reference
assets. Investigate ranked hypotheses, connection paths and timing evidence. Alarms
are caller supplied; no automatic live alarm, causal proof or acknowledgement workflow
is invented.

**Models/history:** inspect synthetic measurement series/ranges/table and run the
existing synthetic forecast targets/models/horizons. Background-job activity,
background scenario queues and retraining/refresh queue controls are temporarily
hidden. Backend lifecycle and cancellation APIs remain available.

## Sources and services

Published readings and station data refresh at the existing visibility-aware cadence,
with original timestamps and stale/unavailable states. The Services disclosure shows
PostgreSQL/Redis/worker status and source/service alerts. All configured application
services should be reached through the Docker web process; an unconfigured direct
Flask process cannot see them automatically. Public-feed freshness is separate from
application service health.

See [frontend structure](FRONTEND_DESIGN.md), [location provenance](GEOGRAPHIC_MAP.md)
and [scientific scope](PHASES.md) for the respective limits.


## Demonstration

Start with `make up` and use port 5050. Keep tokens out of recordings.

1. Home → Network: inspect a sourced geographic pin and station reading; show
   search/filter/reset and an unlocated directory asset. Explain 66 assets versus
   261 dated connection records and the source/quality limits.
2. Services → Demand: distinguish service health from source freshness; inspect
   forecast origin, all 24 hours, model provenance and empirical uncertainty.
3. Research → Simulation: run a short supplied outage; demonstrate Stop separately.
   Explain connectivity versus the aggregate synthetic teaching model.
4. Policy review → Alarm investigation: show synthetic advice, surrogate agreement,
   actual SHAP factors and supplied-alarm hypotheses. Save a review only deliberately
   with an honest demo label/reason; it is not qualified operator-study evidence.
5. Models/history: show the synthetic experiments. Backend job verification is
   optional and submits real software jobs; queue panels are currently hidden.
6. Present the [editable deck](../deliverables/PRISM_Phase3_Demo.pptx) alongside
   [current phase results](PHASES.md). The deck predates the latest model refinement;
   use the register for current metrics and retain failed/unverified targets.
