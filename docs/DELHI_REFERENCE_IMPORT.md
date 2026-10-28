# Delhi reference topology: reconciliation and import

The six original node discrepancies now have documented decisions for the declared
**site-level reference model**. The corrected version contains **66 canonical
assets, 245 dated circuit observations and 16 interface/section assertions**.
Of these assets, **50 source-referenced Delhi substation/plant identities** qualify
for the report's node-count requirement. This is not a complete current switching
snapshot or a power-flow model.

The current review is [RECONCILIATION.md](../data/topology/delhi/RECONCILIATION.md).
The original [AUDIT.md](../data/topology/delhi/AUDIT.md) and original extraction
files remain historical evidence; their earlier issue counts are not the current
reconciliation result.

## What was corrected

| Original issue | Evidence-backed decision |
|---|---|
| Dwarka | Merge the feeder candidate into Dwarka Sector-5. The 2018 steering minutes explicitly connect Sector-5 with the PPK-I/III, Naraina, Budella and PPK-II evacuation names. The DPR distinguishes this site from the existing PPK-I station. Keep voltage/owner assertions separate. |
| Ballabhgarh | Merge the 400 kV candidate into POWERGRID Samaypur, identified as Samaypur/Ballabgarh in POWERGRID records and the 2019 DTL line table. Add the different BBMB 220 kV Ballabhgarh station separately. |
| Wazirabad | Merge the historical Wazirabad record into South of Wazirabad: the older tender and newer directory give the same Garhi/Khajuri Khas address and matching feeder context. Preserve both source names. |
| Narela | Keep DTL and BBMB equipment as owner-specific assets on an extended bus. Group them for reference-site counting. BBMB's register and the regulator report describe this arrangement. Do not invent an inter-site line or count two geographic sites. |
| Budella | Classify as planned/under tendering as of the June 2025 minutes; retain cable observations separately. Exclude Budella from existing-node coverage. No October 2026 commissioning claim. |
| Plants | Record PPS-I and GTPS evacuation at 220 kV Pragati, the PPCL-to-DTL Bawana bus interconnector at Bay 419, and Jhajjar(APCL)–Mundka Ckt-I/II. Preserve historical bus details and keep each plant distinct from its receiving substation. |

SOW abbreviation attribution and Timarpur nominal voltage were corroborated in
the earlier review. They remain resolved metadata findings. No operating values
are inferred from these identity decisions.

All decisions contain source hashes, retrieval metadata and page/table locators
in [identity_resolution.json](../data/topology/delhi/identity_resolution.json).
The source-bound original node records, labels and circuit endpoint IDs remain
available. Remapped observations retain their original endpoint IDs as provenance.

## Correct count and coverage

Review III physical pages 2 and 11 ask for **50 Delhi substation/plant nodes**,
not 50 geographically distinct sites. The previous extra site-count condition was
our interpretation and has been corrected under ADR-017.

The qualifying reference list is the 47 DTL directory assets plus GTPS, PPS-I and
PPS-III. It excludes aliases, the additional BBMB Narela owner portion, external
interfaces and planned Budella. A plant and its receiving substation remain
separate electrical assets even where they share a complex. No number of distinct
geographic sites is asserted.

The review accounts for the assets on the June 2019 schematic, identifies the
missing BBMB Ballabhgarh endpoint, and explains all 15 initial historical comparison
findings using aliases, single-circuit multiplicity or dated LILO changes. The
2019/2023/2025/2026 evidence is not merged into an alleged single operating snapshot.
Additional documented direct interfaces are retained, including Bawana's external
feeds and the historically isolated BTPS–Alwar line. NTPC Dadri and the POWERGRID
Dadri ring reference remain owner-qualified, separate records.

The scope is the declared source-reference inventory. Complete current Delhi
coverage and electrical operating readiness remain unverified. Exact Noida terminal
naming, missing/duplicated circuit suffixes, source length conflicts and current
switching/measurement parameters remain field-level limitations. They are visible
in [reconciled_coverage.json](../data/topology/delhi/reconciled_coverage.json).

## Versioned database representation

The validator uses an undirected `MultiGraph` of reference observations, retaining
parallel circuits, unknowns and islands. The Neo4j database contains:

- One immutable `PrismReferenceDataset` snapshot per content hash.
- 66 `PrismReferenceEntity` asset records.
- 245 `PrismReferenceEntity` circuit-observation records.
- 16 `PrismReferenceEntity` interface-assertion records.
- 522 `REFERENCE_ENDPOINT` relationships, describing endpoint presentation order.

An interface assertion can describe a generation bus connection, extended bus,
historical line group or dated diagram section. It is not automatically an extra
physical transmission circuit or a conducting path. The isolated BTPS–Alwar line
must not be assumed to carry power. Unknown limits, impedance, output and measured
flow stay unknown, and simulation eligibility remains false.

Original nested records and source/review evidence are stored losslessly as JSON.
Repeated imports compare exact properties and endpoint relationships; they never
delete or overwrite datasets. New review content creates a new dataset ID. The
previous local snapshot remains unchanged and available for comparison.

The reference labels are independent of the teaching fixture's `PrismNode`/`LINE`
labels. The website, trained models, simulation inputs and live telemetry were not
changed by this reconciliation.

## Reproduce

```bash
python -m scripts.import_delhi_reference --output data/topology/delhi/reference_dataset.json --review-dir data/topology/delhi
python -m unittest discover -s tests -v
```

Use the local generated credentials without printing or committing them:

```bash
set -a
source .env
set +a
python -m scripts.import_delhi_reference --import-neo4j
```

The local Compose project is `prism-phase3-reference`. Optional dependency setup:

```bash
python -m pip install -e '.[neo4j]'
docker compose -p prism-phase3-reference -f compose.yaml -f compose.phase3.yaml up -d neo4j
```

The live import report is [phase3_reference_import.json](../reports/phase3_reference_import.json).
The original import report is preserved separately. `python -m scripts.verify_delhi_reference`
uses a disposable Neo4j container to test repeat imports, preservation of unrelated
fixtures and rejection of corrupted snapshots. Raw source archive regeneration
requires the matching local originals; the contract tests use tracked project records.

Step 8 can display the corrected source-reference topology with dates, types,
provenance and remaining field limitations visible. Electrical simulation readiness
and real telemetry coverage are separate later requirements.
