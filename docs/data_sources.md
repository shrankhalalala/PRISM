# Source assessment — Phase 1

Assessment date: 2026-09-12. No external measurement dataset has been imported.
Source availability, terms, geography, timestamps, and completeness must be verified
before a production collector or model-training dataset is selected.

| Candidate | Intended use | Evidence / remaining checks |
|---|---|---|
| Delhi SLDC Grid Watch | Delhi demand and frequency | Proposed by Review-II: https://delhisldc.org/grid-watch/ . This audit has not confirmed an accessible historical export or sampling guarantee. Treat as unverified. |
| Ember | Historical electricity context | Official API documentation https://api.ember-energy.org/docs describes API-key access. Methodology https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf discusses monthly/annual data. Verify dataset-specific resolution; do not assume hourly Delhi solar/wind history. |
| NITI Aayog ICED | Plant capacities and metadata | Official https://www.iced.niti.gov.in/energy/ lists power plant details and generation. Export availability, terms and field coverage remain to be checked. |
| CEA Power Maps | Reference topology | Official https://www.cea.nic.in/old/powermaps.html lists transmission maps. Requires manual validation/digitization, voltage and asset matching; map lines alone do not supply electrical impedances. |

Acceptance gate for real forecasting data: timestamped power observations with
known units and cadence, suitable geographic aggregation, permitted reuse,
provenance and coverage audit. For real topology: asset identifiers, verified
connectivity, ratings, and (before power-flow analysis) electrical parameters.
Until then, use the committed synthetic fixtures, clearly labeled in the UI.

## Phase 3 Grid Watch display adapter — verified 2026-10-22

The public Grid Watch frontend calls `https://delhisldc.org/api/dynamic-data` and
refreshes its dynamic readings every 60 seconds. Direct requests returned JSON
without authentication during this check. PRISM uses this same read-only endpoint
instead of scraping rendered HTML. This is an observed website endpoint, not a
documented, versioned API with an availability guarantee.

| Source field | PRISM field | Interpretation |
|---|---|---|
| `DD_DATE` | `observed_at` | Source ISO timestamp; preserve its explicit UTC offset and display IST in the UI |
| `DD_CURR_LOAD` | `demand_mw` | Delhi current load, MW |
| `DD_FREQUENCY` | `frequency_hz` | Published frequency, Hz |
| `DD_DRAWAL` | `drawal_mw` | Current drawal, MW; not total local generation |
| `DD_CURR_SCHEDULE` | `schedule_mw` | Current schedule, MW |

`GET /api/live/gridwatch` validates a complete finite record, rejects naive or
implausibly future timestamps and timestamp regressions, and caches successful
and failed fetch attempts for 60 seconds per Flask process. Requests use an
eight-second timeout, a bounded response size, and native OS certificate
verification through `truststore`. TLS verification remains enabled.

Readings older than 300 seconds are stale even if the HTTP request succeeds. A
failed fetch retains the last good reading and labels it stale; without a previous
reading the API returns HTTP 503 and `status: unavailable`. The browser also ages
its last reading if PRISM becomes unreachable. Cache contents are transient and
reset when the application restarts. Polling occurs on dashboard/API requests;
there is no unattended historical collector. Multiple Flask processes have
independent caches; a shared collector/cache is needed before scaling deployment.

The response includes source URL, feed URL, source time, successful retrieval time,
age, and availability. Source timing and accuracy are reported as published, not
independently certified. The synthetic measurement history is never overwritten,
and these readings are not passed into the existing forecasting or dispatch models.
This feed does not provide the audited solar/wind history or topology needed to
replace those model inputs.

No explicit reuse licence or published API access policy was established in this
check. `/robots.txt` returned the site's HTML shell, rather than a crawl policy.
Public accessibility does not establish redistribution or training rights; retain
source attribution and verify terms before publication or dataset redistribution.

## Phase 3 Step 2: topology source selection — 2026-10-22

The full audited source register, date hierarchy and Delhi 400/220 kV inclusion
rules are in [DELHI_TOPOLOGY_SCOPE.md](DELHI_TOPOLOGY_SCOPE.md). DTL's official
station directory and circuit tables are selected as primary acquisition sources
alongside its dated reference maps. This supplements the report's CEA/NPP routes;
the exact legacy CEA map link redirected to login and NPP did not expose a verified
Delhi station/edge export in this check.

The selected DTL planning PDF was published in October 2019. Its existing-network
map is dated June 2019, distinct from its later planning-map section. The station
directory has a May 2025 content date and circuit tables a September 2024 date.
These sources are not a single verified 2026 operating snapshot. Use field-level
dates and retain unresolved differences in subsequent inventory work.

Step 2 selected and inspected sources; it did not replace the synthetic grid,
import official assets, establish electrical parameters, or map live telemetry.

## Phase 3 Step 3: dated local source archive — 2026-10-22

[The source archive](../data/sources/delhi/README.md) records 17 public-source
attempts: 14 captures and three failures. All eight required DTL references/policy
files succeeded, including the canonical 220 kV transformation page. The captured
CEA login, NPP shell and SLDC frontend remain access-only evidence. NPP capacity
and ICED failed TLS hostname checks; the PPS-III PDF exceeded the 64 MiB cap.

Raw originals are retained locally and excluded from Git pending review of source
redistribution conditions. Catalogs, checksums, response metadata, 17 extraction
locators and a manual review/gap register are project records. The acquisition
command refuses to overwrite snapshots and supports offline integrity checking.

New supporting references are BBMB's 2024-25 annual report, with the relevant
interface evidence on physical page 86 (printed 78), and IPGCL/PPCL's tariff index
and PPS-I filing. The filing is scanned and needs visual/OCR validation before
further metadata extraction. No asset identities/edges have been inferred or
imported, and current POWERGRID coverage remains an explicit gap.

## Phase 3 Step 4: source-referenced node inventory — 2026-10-22

[The node inventory](../data/topology/delhi/README.md) retains all 47 directory
rows and 46 transformation observations from the archived DTL sources. It adds
documented other-owner, generation and endpoint candidates, producing 64 records
with 258 circuit-endpoint occurrences accounted for. Forty-five transformation
observations are assigned; the SOW label remains unassigned pending identity
confirmation. Site/owner/date ambiguities remain open, so 64 records do not mean
64 distinct verified physical facilities or completion of the 50-node goal.

Rules and evidence bind each record to the saved-source checksum and locator.
Historical MVA metadata is separate from current MW, coordinates and operational
status. No new source download, runtime topology replacement or electrical
validation was performed during this offline inventory step.
