# Delhi reference source archive

This is Step 3 evidence for the scope in
[DELHI_TOPOLOGY_SCOPE.md](../../../docs/DELHI_TOPOLOGY_SCOPE.md). It is separate
from `data/raw/grid.json`, measurements, models and runtime application inputs.

## Snapshot 2026-10-22

- [catalog.json](catalog.json): the public official URLs and intended uses.
- [2026-10-22/catalog.json](2026-10-22/catalog.json): immutable catalog copy used
  for this capture, including the source-date and role assumptions.
- [manifest.json](2026-10-22/manifest.json): 17 attempts, 14 captured files and
  three failed requests; UTC retrieval times, final URLs, HTTP/media metadata,
  sizes and SHA-256 fingerprints. Selected public headers only; no cookies saved.
- [locators.json](2026-10-22/locators.json): 17 page/table/serial/text locators
  tied to the exact captured-source fingerprints.
- [review.json](2026-10-22/review.json): manual suitability assessments and eight
  remaining acquisition/reconciliation gaps.
- `2026-10-22/raw/`: the untouched local source originals. This folder is ignored
  by Git; the originals are preserved on this workstation, not bundled into a
  published repository. The capture does not grant source redistribution rights.

The 14 captures consist of **11 reference/policy files and three access-only
pages**. A captured CEA login page, NPP dashboard shell or SLDC frontend shell
must not be counted as a topology map or inventory. All eight required DTL
references/policy captures succeeded, including the recovered canonical 220 kV
transformation page. This establishes source availability, not asset correctness.

Source dates remain distinct from retrieval dates. No snapshot here certifies
that an asset was operating on the retrieval date. The snapshot does not certify
50 real nodes, a complete circuit inventory, electrical feasibility or telemetry.

## Verified extraction starting points

| Source | Locator | Observed coverage / use |
|---|---|---|
| SRC-01, DTL Rev-02 plan | Physical PDF pages 29-35; planning map separately on 130 | Historical June 2019 network narrative, map, circuits and transformation. Planning works stay separate. |
| SRC-02, DTL stations | HTML tables 1 and 2 | Four 400 kV entries and 43 220 kV entries, before alias/status reconciliation. |
| SRC-03, DTL 400 kV lines | HTML table 1 | 14 numbered source rows; circuit sections and duplicate endpoint pairs require correct modeling. |
| SRC-04, DTL 220 kV lines | HTML table 1 | 115 numbered source rows. Serials 88/89 repeat circuit-I; no silent correction. |
| SRC-05, 400 kV transformation | HTML table 1 | Four numbered station entries, with historical MVA metadata. |
| SRC-06, 220 kV transformation | HTML table 1 | 42 numbered source rows; includes multiple transformation levels at some facilities. These are not 42 new physical stations to append to the directory. |
| SRC-13, BBMB Annual Report 2024-25 | Physical PDF page 86, printed page 78; section J, items I-II | Maintenance evidence for the Delhi interface including Narela-Rohtak Road circuits I/II. Not a full network list. |
| SRC-14, IPGCL/PPCL filing index | Dated upload text anchors and official links | Later plant-filing references; identifies the source URLs without assuming every target was captured. |
| SRC-15, PPS-I petition | Physical PDF pages 1-2, visually inspected | Plant/company identity and tariff periods. Scanned PDF, dated 30 January 2026 on these pages; the index's 5 February upload is a separate date. No capacity/wiring fields extracted yet. |

HTML tables are numbered one-based in the saved HTML. Serial numbers mean the
source table's first column, not the physical `<tr>` number. PDF page references
are physical one-based pages; printed labels can differ. Table counts are
unreconciled evidence counts, not graph node/edge acceptance counts.

## Access gaps retained

1. CEA's legacy map route returns a login page. No authentication/CAPTCHA bypass
   was attempted; a current public replacement map remains unverified.
2. NPP capacity and ICED portal requests failed certificate hostname verification.
   TLS validation was not disabled. Correct official URLs/alternative sources
   need verification before those portals can supply data.
3. The PPS-III petition response exceeded the 64 MiB cap. It was not stored as a
   truncated PDF. Its index URL and failed attempt remain in the manifest.
4. Current POWERGRID commissioning/circuit coverage is incomplete. DTL's dated
   other-owner descriptions and BBMB's interface evidence are starting points.
5. The PPS-I filing needs visual/OCR-assisted extraction of any further fields.
6. Timarpur's voltage text and the repeated circuit label remain unresolved.
7. The sources have mixed dates, not a single 2026 operating-state reference.
8. Original-source redistribution conditions need review before publication.

These gaps do not erase the captured DTL source set. They must carry into Steps
4-6 so unknown facts and incomplete coverage remain visible.

## Commands and integrity guarantees

From the repository root with the project dependencies installed:

```bash
python -m scripts.acquire_topology_sources --verify data/sources/delhi/2026-10-22
python -m scripts.acquire_topology_sources --output-dir data/sources/delhi/NEW-SNAPSHOT
```

The first command uses no network. It checks the frozen catalog checksum, source
set, required capture outcomes, saved-byte sizes/checksums, PDF signatures and
locator-to-source fingerprints. It needs the original local `raw/` files; a new
Git clone contains the catalog/manifests/locators, not these ignored originals.

The second command fetches current responses into a **new** directory, using
native OS TLS verification, bounded response sizes, a 20-second socket timeout,
three workers and one attempt per URL. It never overwrites an existing snapshot
or tries to log in. Socket timeouts are not a hard wall-clock deadline for an
entire large transfer. Failed optional references remain explicit; a required
capture failure makes the command fail its integrity gate.

A later download may differ because a source changed, or because an HTML page
contains changing counters/tokens. It must receive its own manifest; never edit
the old fingerprints to make changed bytes pass. Source-byte identity is not a
claim that the publisher's facts are correct. Manifests are project records, not
cryptographically signed publisher attestations.

No application endpoint, runtime fixture or trained artifact was changed for
Step 3. Node/circuit normalization and inference belong to the next inventory
steps, using these source references and the unresolved-items register.

## Follow-up reconciliation captures

`reconciliation_catalog.json` selects four additional official DTL references:
March 2026 OCC agenda, June 2025 steering minutes, the Timarpur transformer tender,
and the FY2023-24 ARR petition. `2026-10-22-reconciliation` preserves the initial
sandbox DNS failures. `2026-10-22-reconciliation-verified` preserves the separate
successful verified-TLS captures (four of four). Neither earlier snapshot was
rewritten. The original 17-source archive counts above are unchanged.

The petition's `2023-24` catalog date denotes its fiscal reference period, not an
independently verified filing/publication date. March 2026 refers to the OCC agenda
period; its cover gives the meeting date 24 March 2026. PDF physical page locators
and interpreted conclusions are in the project's `reconciliation_review.json`.
Raw originals stay ignored under the same archive rules. Verify the follow-up:

```bash
python -m scripts.acquire_topology_sources --verify data/sources/delhi/2026-10-22-reconciliation-verified
```

SRC-19's catalog date `2022-05-30` follows the dated tender reference
`DTL-8650-300522`; it is not an independently verified publication timestamp.
The captured page explicitly gives the tender opening as 20 June 2022. Neither
date establishes commissioning or current operating status.

## Identity and terminal evidence follow-up

The `identity`, `terminals`, `terminal-followup` and `cea` snapshots dated
2026-10-22 record subsequent official reference attempts. Failed legacy CEA/NRPC
routes remain failed captures; they are not used as resolved identity evidence.
The regulator PDF was recovered at its official hostname without `www` and is
captured as SRC-33. Review decisions use captured, hash-matching sources only.

`identity_resolution.json` records exact page/table locators, source dates and
retrieval metadata. The June 2019 schematic was visually reviewed; page 133 of the
DTL transformer tender supplies the old Wazirabad address; the regulator report's
physical page 122 describes Narela's extended-bus portions; the November 2025
DTL minutes' physical page 7 names the PPCL/DTL Bawana bus interconnector.
The original 17-source acquisition figures are historical and unchanged.
