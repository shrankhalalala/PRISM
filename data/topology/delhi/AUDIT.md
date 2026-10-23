# Delhi topology audit — Steps 5–6

**Result: the topology acceptance gate has not passed.** The circuit inventory and
audit are reviewable; completeness and electrical readiness remain unverified.

This is the initial extraction audit. The later [identity review](RECONCILIATION.md)
records dispositions for the six original node cases and corrects the report-count
interpretation. Original findings stay preserved here; electrical readiness is separate.

## Coverage reviewed

| Evidence | Coverage |
|---|---|
| DTL station directory | 47/47 entries in the Step 4 node inventory |
| Later DTL circuit tables | 129/129 rows: 14 at 400 kV, 115 at 220 kV |
| June 2019 DTL circuit tables | 113/113 rows: 12 at 400 kV, 101 at 220 kV |
| BBMB annual report 2024–25 | 3 named circuit observations on physical page 86 |
| Total dated circuit observations | 245; not a count of distinct current lines |
| Additional historical connection narratives | 7 claims retained separately; no inferred electrical edges |
| Transformation tables | 46 observations retained; SOW remains unassigned |

Source-byte hashes, source dates, retrieval times and row/page locators are in
[circuits.json](circuits.json). [circuits.csv](circuits.csv) is the compact review list.
The historical transcription and supplemental review inputs are pinned by hash.

## Findings that prevent acceptance

- Eight node identity/status issues remain in [unresolved.json](unresolved.json).
- Twelve later DTL rows reference unresolved Dwarka or Ballabhgarh endpoint candidates.
- Four later source labels omit a circuit number (SRC-04 rows 27, 40, 41 and 57).
- SRC-04 rows 88 and 89 both state R.K. Puram–Trauma Centre Ckt-I. Both observations
  are retained and flagged. No second circuit number or physical line is assumed.
- Fifteen historical rows lack an exact endpoint/voltage/circuit-label match in
  the later tables. Absence is not retirement evidence.
- The 2019 map and external/plant terminals are not fully reconciled. DTL-owned
  circuit tables cannot establish complete POWERGRID/BBMB/generation coverage.
- Sources span different years. No single 2026 operating snapshot is established.
- Coordinates, current status, MW limits, impedance and actual flows remain unknown.
- 64 node records do not establish 50 distinct verified Delhi physical sites.

## Nodes with no connection in the later DTL tables

This is a source-coverage diagnostic, not evidence that the assets are disconnected
in reality. BBMB observations and historical rows are kept outside this dated-table
diagnostic rather than mixed into one apparent operating snapshot.

- `plant-jhajjar`
- `plant-pps1`
- `plant-pps3-bawana`
- `ss-dadri-pgcil`
- `ss-dwarka-sector-5`
- `ss-narela-bbmb`
- `ss-noida`
- `ss-noida-62`
- `ss-panipat-bbmb`
- `ss-rohtak-road-bbmb`
- `ss-samaypur-pgcil`
- `ss-timarpur`

## Historical observations without an exact later match

| Source row | Voltage | Historical label | Circuit |
|---|---|---|---|
| SRC-01 serial 1 | 400 kV | Mandola – Bawana | I |
| SRC-01 serial 2 | 400 kV | Mandola – Bawana | II |
| SRC-01 serial 7 | 400 kV | Tuglakhabad- Samaypur (Ballabgarh) | I |
| SRC-01 serial 8 | 400 kV | Tuglakhabad- Samaypur (Ballabgarh) | II |
| SRC-01 serial 13 | 220 kV | Pappankalan-III – Pappankalan-I | I |
| SRC-01 serial 14 | 220 kV | Pappankalan-I – Naraina | I |
| SRC-01 serial 15 | 220 kV | Pappankalan-III – Naraina | I |
| SRC-01 serial 18 | 220 kV | Kanjhawala – Najafgarh | I |
| SRC-01 serial 20 | 220 kV | Mundka – Kanjhawala | I |
| SRC-01 serial 31 | 220 kV | Wazirabad– Gopalpur | I |
| SRC-01 serial 32 | 220 kV | Wazirabad– Gopalpur | II |
| SRC-01 serial 76 | 220 kV | Naraina – Ridge Valley | I |
| SRC-01 serial 87 | 220 kV | Patparganj - Gazipur | I |
| SRC-01 serial 92 | 220 kV | AIIMS –Ridge Valley | I |
| SRC-01 serial 93 | 220 kV | AIIMS –Ridge Valley | II |

## Evidence needed before electrical/model integration

1. **AUDIT-MAP-COVERAGE** — Reconcile every in-scope historical ring/map connection and terminal against tables; map crossings are not junctions. External Dadri/Noida/Jhajjar and plant interfaces are not fully covered by DTL-owned tables.
2. **AUDIT-BBMB-COVERAGE** — Three named BBMB maintenance observations are recorded (Panipat–Narela III and Narela–Rohtak Road I/II). Confirm exact buses, full interface coverage and snapshot alignment before electrical import.
3. **AUDIT-HISTORICAL-DIFFERENCES** — Resolve the listed historical-only observations and source date/length conflicts without mixing snapshots.
4. **AUDIT-TRANSFORMER-TERMINALS** — Resolve SOW; define voltage-level buses and transformer terminal semantics. Site-level MVA observations are not inter-site transmission edges.
5. **AUDIT-NODE-IDENTITY** — Resolve the eight node issues, physical-site counting and Delhi geography. Do not claim the 50-node or 500+ scalability goals from record counts.
6. **AUDIT-CIRCUIT-IDENTITY** — Resolve duplicate/incomplete circuit labels and endpoint candidates; obtain independent current owner/terminal records.

The eight source-access/date/reuse gaps remain linked in [topology_audit.json](topology_audit.json).
Resolving a source gap does not automatically close an asset/circuit issue.

## Decision

Hold Step 7 electrical/model integration until the above evidence is reconciled.
No Neo4j import, runtime topology, dashboard, trained model or simulation was changed.
Step 5 has a source-referenced inventory; full T03 verification is pending.
Step 6 has an audit result; its completeness acceptance checkpoint remains open.

Reproduce offline with matching original sources available:

```bash
python -m scripts.build_delhi_circuit_inventory --check
python -m unittest discover -s tests -v
```
