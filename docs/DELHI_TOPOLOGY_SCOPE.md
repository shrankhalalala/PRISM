# Delhi topology scope and source specification

Step 2 completed: 2026-10-22. Scope version: `delhi_ehv_reference_v1`.
This is a reference-data specification, not an imported topology or a claim that
the complete Delhi network has already been reconstructed.

## 1. Boundary decision

Build a source-dated reference model of the **400 kV and 220 kV transmission
system serving NCT Delhi**, including directly connected external supply
endpoints and verified generating-station connections. Use Delhi Transco Limited
(DTL), the state transmission utility, as an additional primary source alongside
the CEA/NPP sources proposed by the reports.

The boundary is functional as well as geographic: retain a documented endpoint
needed to represent a circuit serving Delhi even when that endpoint lies outside
the NCT or belongs to POWERGRID/BBMB/another utility. Ownership alone does not
determine whether an asset is inside or outside Delhi.

Do not recursively expand those external endpoints into the national network.
An external station's internal equipment is included only when necessary and
independently documented for the Delhi interface. Record its actual voltage and
owner; a 765/400 kV station is not a reason to model the entire 765 kV system.

## 2. Inclusion and exclusion rules

| Category | Include in this scope | Keep separate / exclude from the initial circuit model |
|---|---|---|
| DTL substations | Every source-listed 400/220 kV station within the declared reference network; reconcile all named entries even if some metadata is unknown | No selection of only the easiest or largest stations |
| Other owners | Delhi-serving POWERGRID, BBMB and other-utility stations/connections supported by the source tables/maps | A DTL-only list is not a complete multi-owner network inventory |
| Generating stations | Named generation facilities with verified connections to the in-scope network; preserve separate plant and switchyard identities when justified | Do not turn a substation named BTPS/IP/Rajghat into a currently operating generator merely from its name |
| External supply | The immediate named remote endpoint of each verified boundary circuit, its owner and circuit identity | No generic fictional wind/import plant as a substitute for real interfaces; no whole-NCR expansion |
| Lines | Source-confirmed 400/220 kV circuits, including parallel circuits and cable/overhead sections where separately documented | No edge inferred merely because two sites are nearby or drawn crossing on a map |
| Transformers | Verified voltage ratios, IDs/counts and MVA ratings at included stations, when documented | Do not convert transformer MVA to guaranteed dispatchable MW or infer impedance/ramp limits |
| Lower voltages | Record 66/33/11 kV transformation and downstream delivery metadata when available at included stations | Initially exclude complete lower-voltage feeder/distribution topology; downstream station expansion requires a separate scope revision |
| Loads | Verified delivery points may later attach to stations; report supplied demand at its actual aggregation level | Do not invent district load nodes or split Delhi/DISCOM totals among stations without an explicit, labeled estimation model |
| Development status | Preserve documented existing, proposed, under-construction, retired and unknown states separately | Proposed/spillover works do not become operating assets because a planning map contains them |

For geographically ambiguous sites, keep `boundary_classification: unresolved`
until the source/address/location evidence is reconciled. The schematic is not
to scale and must not be used to manufacture latitude/longitude.

## 3. Counting rules and the report's 50-node goal

The inventory must report **physical facilities**, **graph vertices**, **voltage
levels**, **circuits**, and **boundary endpoints** separately. Count a physical
station once after aliases are reconciled. Voltage-layer or bus vertices may
later be necessary for a correct graph, but must not be presented as additional
physical stations to inflate coverage. Co-located plant and station assets need
evidence for their separate identities.

The report's minimum 50 Delhi-node goal remains tracked, along with a separate
500+ scalability test. Never add invented nodes, duplicate aliases, proposed
stations labeled existing, or arbitrary district loads to meet the threshold.
If the verified boundary has fewer qualifying physical assets than expected,
report the shortfall and evidence before changing scope.

**Preflight observation, not a final inventory:** SRC-02 has four entries under
400 kV and 43 under 220 kV (47 listed entries). SRC-07's older summary gives four
and 42 as of 31 March 2023. These are differently dated source counts, not a
2026 census. They omit any other-owner/plant/boundary additions needed by this
scope and require alias/status reconciliation. A station directory does not
establish a complete circuit graph or the operating status of every listed asset.

## 4. Time boundary and reference hierarchy

There is no verified single-date 2026 operating snapshot in the sources examined.
Use two explicitly dated evidence layers:

1. **Historical connectivity anchor:** SRC-01, published October 2019, especially
   its existing-network material dated June 2019. Its physical page 30 is the
   existing-network schematic; pages 31-33 list circuits and pages 34-35 cover
   transformation. Page 130 is a planning map with a mixed existing/proposed
   legend and is a cross-check, not an as-built replacement.
2. **Later reference updates:** SRC-02's station list (content updated 14 May
   2025) and SRC-03/SRC-04 circuit tables (content updated 18 September 2024).
   Preserve differences from the historical layer, including unknown effective
   commissioning/retirement dates. A webpage update date is not an asset date.

Resolve identity/connectivity using a circuit or commissioning record before a
schematic approximation. A newer source is preferred only for fields and asset
status it actually documents; do not silently combine contradictory facts into a
fictitious single-time network. Retain `source_date`, `observed_at`, and where
known `effective_from`/`effective_to` with each assertion.

The eventual dataset label must describe a **source-dated Delhi EHV reference
network**. It must not say "live Delhi topology" or "as of October 2026" until
the status/coverage evidence supports that claim. Live telemetry freshness is a
separate property from topology freshness.

## 5. Audited source register

All checks below were made on 2026-10-22. HTTP access is evidence of retrieval,
not a guarantee of completeness, accuracy, reuse rights or continued availability.
The old `delhitransco.in` host failed certificate hostname verification; the
canonical `dtl.gov.in` pages were reached through official navigation and retrieved
with TLS verification enabled.

| ID | Official source | Source date / access result | Role and limits |
|---|---|---|---|
| SRC-01 | [DTL 13th Plan, Rev-02, 2017-18 to 2021-22](https://www.dtl.gov.in/WriteReadData/CMS/13thBusinessPlan_2017-18_2021-22_Rev-02.pdf) | Cover: October 2019; 147 pages; PDF retrieved successfully | Historical topology anchor and map legend. Inspect physical pages 29-35 and 130. Distinguish existing from proposed works; no 2026 operating-status claim. |
| SRC-02 | [DTL List of Substations](https://dtl.gov.in/content/326_1_ListofSubstations.aspx) | Content updated 14 May 2025; HTTP 200 | Facility names, voltage headings and addresses. No complete circuit connectivity or current generator-status evidence. |
| SRC-03 | [DTL 400 kV circuits](https://dtl.gov.in/content/160_1_Lines400KV.aspx) | Content updated 18 September 2024; HTTP 200 | Named circuit endpoints, circuit distinctions, lengths and conductor descriptions. Some lengths cover only the DTL portion; not line MW limits or a whole-owner-network inventory. |
| SRC-04 | [DTL 220 kV circuits](https://dtl.gov.in/content/159_1_TransmissionLines220KV.aspx) | Content updated 18 September 2024; HTTP 200 | Endpoint/circuit evidence and metadata; spelling/serial/circuit-label anomalies need reconciliation. |
| SRC-05 | [DTL 400 kV transformation](https://dtl.gov.in/content/177_1_Substation400KV.aspx) | Content updated 4 March 2020; page inspected | Voltage ratios and MVA metadata; historical, not current available MW. |
| SRC-06 | [DTL 220 kV transformation](https://www.dtl.gov.in/content/178_1_Substation220KV.aspx?format=Print) | Search-indexed content states 4 March 2020; direct web-reader retrieval failed | Candidate cross-check only; direct capture/revalidation remains for Step 3. |
| SRC-07 | [DTL network overview](https://dtl.gov.in/Content/18_1_OurBusiness.aspx?format=Print) | Content updated 18 September 2024; counts explicitly as of 31 March 2023 | Establishes the 400/220 kV system focus and historical count cross-check; not an asset inventory. |
| SRC-08 | [CEA legacy power-map link](https://cea.nic.in/old/powermaps.html) | Redirected to CEA login in this check | The report's exact URL did not expose a public map. No authentication/CAPTCHA bypass attempted. Find a current public map route in Step 3 if available. |
| SRC-09 | [NPP transmission dashboard](https://npp.gov.in/dashBoard/trans-map-dashboard) | Page accessible; public reader exposed aggregate summaries/placeholders | No usable Delhi endpoint-level export verified. Supplementary candidate, not the inventory backbone. |
| SRC-10 | [NPP capacity dashboard](https://www.npp.gov.in/dashBoard/cp-map-dashboard) and [ICED energy portal](https://www.iced.niti.gov.in/energy/) | Web-reader requests timed out | Candidate plant metadata; coverage/export availability unverified. Do not assume working APIs. |
| SRC-11 | [Delhi SLDC Grid Watch](https://delhisldc.org/grid-watch/) | Existing display adapter verified earlier on this date; not re-polled for topology | Later telemetry mapping. Aggregate measurements cannot establish wiring or individual station demand. |
| SRC-12 | [DTL copyright policy](https://dtl.gov.in/content/14_2_CopyrightPolicy.aspx) | Content updated 19 December 2014; HTTP 200 | States restrictions on alteration/commercial exploitation. Preserve original evidence and attribution; this check does not establish a general licence to redistribute modified maps/datasets. |

SRC-01 downloaded-byte fingerprint:
`54b6a73bc2a89522df97245820f027ac19e6dbda314d84fda738644fc5d88026`.
Inspected copies are temporary local evidence for source selection. Archiving
permitted source snapshots, timestamps, checksums and extraction locators is
Step 3; no raw official documents or source inventories are added to the runtime
dataset by this step. Dynamic webpage counters/tokens can change raw HTML hashes.

## 6. Boundary candidates and identity issues to carry into acquisition

The official tables/maps justify checking at least the following cases; these
are reconciliation tasks, not a completed asset list or approved alias mapping:

- External/interface endpoints named in SRC-03 and SRC-01, including Mandola,
  Jhatikara, Ballabhgarh/Samaypur, Dadri, Noida and the documented generation
  connections. Verify geography, owner, voltage and exact terminal/circuit before
  assigning `internal` or `external_boundary`.
- Tikri Kalan / Mundka and differently spelled Pappankalan, Kanjhawala, Gazi/Ghazipur,
  Tughlaqabad and Maharani Bagh records. Keep source spellings as aliases only
  after identity evidence is checked; similar place names do not prove identity.
- Separate a generating station from a same-named switchyard/substation and
  record retired/unknown generation explicitly. A legacy map or a zero feed value
  cannot establish present operating capacity.
- SRC-04 repeats the R.K. Puram-Trauma Centre circuit-I label in serials 88-89.
  Do not silently rename the second circuit to II without corroboration.
- SRC-02's Timarpur address has an apparent `20/33kV` text inconsistency under
  the 220 kV heading. Verify the actual voltage before using it in electrical
  modeling. The directory entry can remain an unresolved inventory candidate.
- Apparent map crossings, split buses and DTL/POWERGRID ownership sections need
  explicit terminal semantics. Do not sum a DTL-only length as the whole circuit
  or merge split buses without documenting the abstraction.

## 7. Required outputs of the next steps

Step 3 will preserve suitable source evidence and field-level locators, record
access/reuse limitations and identify missing owner/commissioning references.
Steps 4-5 will construct node and circuit inventories with provenance and an
unresolved-items register. Step 6 will reconcile completeness before importing
the graph or changing the live dashboard.

Each future asset/connection assertion needs at least: stable ID, source spelling,
asset/circuit type, source ID and locator, publication/as-of date when known,
verification state, known/unknown operational state and boundary classification.
Unknown ratings, output, impedance and station telemetry stay unknown. Use a
separate simulation-eligibility flag once the required parameters are available.

## 8. Step 2 completion and remaining gates

- [x] Delhi 400/220 kV geographic/functional scope defined.
- [x] External endpoint, lower-voltage and generation inclusion rules defined.
- [x] Historical map and later update source dates inspected and distinguished.
- [x] Canonical station/circuit sources selected; report-source access gaps recorded.
- [x] Physical-asset counting and 50/500+ target treatment defined.
- [x] Dated-reference versus current-operating-network claims separated.
- [x] Archive/revalidate selected source snapshots and record unresolved access gaps (Step 3); see the [source archive](../data/sources/delhi/README.md). Missing public routes remain explicit gaps, not completed source coverage.
- [ ] Produce and reconcile all node and edge inventories (Steps 4-6).
- [ ] Import or display the verified real network (Steps 7-8).

The synthetic 12-node dataset, simulation, models and dashboard behavior are
unchanged. No 50-node completeness, current operating status, electrical
feasibility, or telemetry coverage has been established by this scope document.

Step 4 follow-up: the [node inventory](../data/topology/delhi/README.md) now
accounts for every selected DTL directory row and circuit endpoint occurrence.
Its unresolved site identities are retained explicitly. Edge inventory and the
combined completeness audit remain pending; the gate above is not yet complete.

Steps 5–6 follow-up: the [circuit inventory and audit](../data/topology/delhi/AUDIT.md)
retain 245 dated observations and seven separate narrative claims. All selected
2019/later DTL circuit-table rows are accounted for, and three named BBMB circuits
are recorded. The completeness audit **does not pass** the integration gate:
map-only and other-owner interfaces, physical identity, terminal semantics and
source contradictions remain unresolved. The combined Steps 4–6 reconciliation
checkbox above stays open. Step 7 has not begun.

Reconciliation/Step 7 follow-up: additional official DTL documents corroborate
SOW attribution and Timarpur nominal voltage, leaving six node issues in the
reference overlay. Under ADR-016, the [reference importer](DELHI_REFERENCE_IMPORT.md)
stores versioned evidence in separate Neo4j labels. This advances source inspection
without claiming electrical completeness. The earlier audit's electrical/model
hold remains in force; no simulation fixture or live dashboard was replaced.

Current identity correction: [RECONCILIATION.md](../data/topology/delhi/RECONCILIATION.md)
records the six dispositions. The report's threshold concerns substation/plant
asset nodes, not geographically distinct sites; the earlier stricter interpretation
is corrected by ADR-017. The 50 qualifying Delhi reference identities exclude
duplicate aliases, planned Budella, external assets and the additional Narela owner
portion. New direct boundary evidence adds BBMB 220 kV Ballabhgarh, NTPC Dadri,
Alwar, Bhiwani and Bahadurgarh interfaces. This is not recursive national expansion;
the earlier Bhiwani exclusion concerned upstream 765 kV context. Sources retain
their own dates, and complete current operating coverage remains unverified.
