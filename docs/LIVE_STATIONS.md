# SLDC station measurements

Step 9 reads the public `https://delhisldc.org/api/grid-loading` endpoint with
native TLS verification, bounded response size and an eight-second timeout.
The website's public application bundle identifies this route; no private access
or credentials are required. The 2026-10-23 captured response is recorded in
`reports/phase3_station_feed.json` with source and observation times.

`data/topology/delhi/telemetry_mappings.json` explicitly maps 49 exact source labels
to 49 canonical reference assets, referencing each asset's evidence. No fuzzy
matching runs in production. HCM Lane is Electric Lane's directory address;
Wazirabad follows the reconciled South of Wazirabad identity. Narela belongs to
the DTL station scope and is not copied to BBMB. CCGT-Bawana is switchyard loading,
not verified gross generation. Badarpur and IP Power map to substations, not
retired generating units. Unknown/new labels are reported for review.

`GET /api/live/stations` includes coverage against all reference assets.
`GET /api/live/assets/<id>` returns a measurement or explicit unavailable state.
The reference snapshot itself is immutable. MW/MVAR signs are retained; voltage
must be nonnegative; all values finite. Qualified source times are required.
The raw RTU status and unverified power-sign convention are exposed as quality
limitations. A zero measurement never proves a station is de-energized.

Concurrent calls share a once-per-minute fetch per process. Failures are throttled
and preserve prior readings as stale; measurements older than five minutes are
stale even after a successful fetch. Backward source timestamps are rejected.
Multiple web processes do not provide a global collector lock; Step 10's dedicated
collector and durable stream address that boundary. There is no claim that the
source updates every six seconds or that measured MW is an electrical line limit.
