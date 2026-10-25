# Delhi topology simulation

The Simulation View uses the exact asset and connection IDs returned by
`/api/reference-grid`. Each run loads that same validated, content-addressed
reference export. The existing aggregate/Q-learning simulator remains a separate
advanced research lab with its original synthetic fixture.

This model computes hypothetical connectivity changes. It includes the reference
export's dated circuit observations and interface assertions; their presence does
not establish concurrent conducting lines, equipment availability or an operating
snapshot. Electrical parameters and simulation-eligibility gates remain unchanged.
The model reports component membership, active reference records and isolated
assets. Station MW, electrical flow, voltage, protection and dispatch effects are
not calculated.

## Streaming execution

`POST /api/topology-scenario/stream` accepts JSON:

```json
{
  "steps": 24,
  "interval_ms": 250,
  "faults": [{"asset_id": "ss-bamnauli", "step": 4, "duration_steps": 4}]
}
```

Targets may be existing Delhi asset IDs or individual connection-record IDs.
Steps are integers from 1 to 96, intervals from 100 to 1000 ms, and at most eight
outages may be supplied. Unknown IDs, synthetic fixture identities and unexpected
fields are rejected. Overlapping outages for the same target remain active until
all matching intervals end.

The response is newline-delimited JSON (`application/x-ndjson`, `no-store`). A
`start` record carries the exact dataset, identities, schematic positions, edges,
assurance and baseline. Each subsequent `step` is computed after the configured
wall-clock interval and emitted immediately. A `complete` event marks completion;
an interrupted stream is not a completed run. The Simulation View consumes these
records while the request remains open.

The illustrative model clock advances 15 minutes per step. The wall-clock update
interval controls viewing pace; neither clock represents a current Delhi outage.
Stop closes the stream. Runs are transient and do not alter stored evidence, live
readings or operations history. Queued aggregate jobs use the separate worker rail.
One topology stream per web worker leaves capacity for other requests; a busy
worker returns HTTP 429. Closing the stream releases its slot.

## Connectivity interpretation

An asset outage removes that vertex and blocks its incident reference records for
its specified interval. A connection outage removes only that record; a parallel
record remains available. Restoration recomputes from the unchanged reference
export. Existing isolated assets remain visible in the baseline; newly isolated
assets are reported separately. Component counts describe the constructed graph,
not electrical islands or measured supply interruptions.
