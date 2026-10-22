# Delhi node inventory — Step 4

Built offline from the [2026-10-22 source archive](../../sources/delhi/README.md)
under the [Delhi EHV scope](../../../docs/DELHI_TOPOLOGY_SCOPE.md). This inventory
is source-referenced working evidence. It is not an imported network, a verified
2026 operating graph, or a count of independently verified distinct physical sites.

## Recorded coverage

| Item | Result |
|---|---|
| DTL directory rows | All 47 represented, with pinned stable IDs and exact source names |
| Inventory records | 64: 58 substation records, 4 plant records, 2 unresolved endpoint candidates |
| DTL transformation observations | All 46 retained; 45 assigned, one SOW record held for identity confirmation |
| Current-table circuit endpoint mentions | All 258 occurrences from 129 source rows mapped to inventory records |
| Mentions with unresolved endpoint identity | 12 occurrences, involving Dwarka or 400 kV Ballabhgarh labels |
| Open node-level reconciliation issues | 8, recorded explicitly |
| Verified unique physical-site count | Not established; a record count is not a site count |
| Minimum 50 verified nodes | Not claimed as achieved; completeness review remains Step 6 |

The 47 directory identities are supplemented with historically documented
other-owner/interface records, source-listed generation identities and circuit
endpoints absent or ambiguous in the directory. No arbitrary districts, fictional
plants, bus duplicates or upstream 765 kV context nodes were added to reach a
numeric target. Supplementary records can still represent ambiguous or co-located
sites; the 64 IDs must not be reported as 64 verified physical stations.

## Files and provenance

- [nodes.csv](nodes.csv): compact human-readable inventory. Voltages and owners
  are **source-reported**, sometimes historical or voltage-specific, not current
  electrical/operating verification.
- [nodes.json](nodes.json): full records and evidence dictionary. Each node,
  alias, ownership/voltage assertion and transformation observation links to a
  source ID, source-byte SHA-256, date, retrieval time and locator.
- [identity_rules.json](identity_rules.json): reviewed directory-ID assignments,
  explicit source-qualified aliases, supplemental assertions and unresolved
  mappings. These are project identifiers, not official global asset IDs.
- [endpoint_mentions.json](endpoint_mentions.json): individual raw endpoint labels
  and node references. These support node coverage; they are **not validated
  source-target edges**, line ratings, switching directions or circuit status.
- [transformation_mentions.json](transformation_mentions.json): all original
  transformation observations, including the unassigned SOW record. Source MVA
  totals/configurations are retained separately from available MW.
- [coverage.json](coverage.json): source-row/record totals and explicit unverified
  physical-count/50-node flags.
- [unresolved.json](unresolved.json): eight open identity/status issues plus
  context excluded from the inventory.

The full inventory records hashes of the source manifest and identity rules.
PDF assertions were manually reviewed against the archived material and page
locators; the builder does not pretend to OCR scanned PDFs or infer map topology.
HTML rows are extracted from the exact saved originals, with declared encodings
honored. Public contact telephone numbers and source signatures are not copied
into the inventory.

## Identity and uncertainty rules

1. Typography normalization can remove punctuation/spacing but cannot silently
   merge different letters, Roman numerals, owners or site suffixes. Nontrivial
   spellings/abbreviations use explicit reviewed project mappings. They remain
   subject to independent completeness review, not fuzzy matching.
2. Bawana substation and PPS-III/Bawana plant, and Pragati substation and PPS-I
   plant, remain separate records. BTPS/Rajghat directory names do not create
   currently operating generating plants.
3. DTL Narela and BBMB Narela remain owner-qualified records with an open
   co-location/physical-site question. Wazirabad is not automatically renamed or
   merged into South of Wazirabad. The SRC-06 SOW abbreviation is retained as an
   unassigned observation with a candidate match, not an asserted alias.
4. Dwarka feeder labels are not automatically identified with Dwarka Sector-05
   or the historical proposed ISTS site. The 400 kV Ballabhgarh label is not
   automatically identified with Samaypur or a BBMB 220 kV facility.
5. Timarpur's source voltage heading/address conflict remains visible. Its
   conflicted heading is excluded from the CSV voltage summary. Budella's
   planning-map status and later circuit mentions do not prove commissioning.
6. Shared PGCIL/DTL voltage-level ownership at Maharani Bagh and Tughlakabad is
   recorded as dated assertions on a site record, not separate fake sites.
   Electrical terminals/buses still require the next graph-modeling steps.
7. Every current operating status, measured output, available MW and precise
   coordinate remains unknown. `simulation_eligible` is false. Source-reported
   MVA and historical observations cannot supply these values implicitly.
8. Geographic classifications are conservative: directory addresses support an
   internal reference classification, while supplemental sites remain unresolved
   unless independently established. Ownership alone does not establish location.

Plant and missing-interface fields still require additional evidence. The node
inventory is complete for the declared directory and endpoint-row coverage,
not for every current asset in Delhi or every proposal on the planning map.

## Rebuild and verify

From the repository root with the original local archive available:

```bash
python -m scripts.build_delhi_node_inventory
python -m scripts.build_delhi_node_inventory --check
python -m unittest discover -s tests -v
```

The builder first verifies the archive. It then checks the exact directory row
set/names against the identity rules, rejects ambiguous/unreviewed label matches,
preserves source serials and emits deterministic JSON/CSV. `--check` regenerates
in memory and compares the existing files without writing. A clone without the
ignored originals can inspect these project records and run their contract
tests, but needs the matching archived bytes to regenerate them.

The runtime still reads `data/raw/grid.json`. No real-network graph, Neo4j data,
simulation profile, trained model, API or dashboard was changed in Step 4.
Step 5 will construct the source-backed circuit inventory; Step 6 will review
the combined node/circuit coverage and unresolved identities before import.
