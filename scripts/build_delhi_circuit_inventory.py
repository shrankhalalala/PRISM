"""Build dated circuit observations and a conservative completeness audit offline."""

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re

from scripts.build_delhi_node_inventory import (
    DEFAULT_ARCHIVE, DEFAULT_OUTPUT, bind_alias, build_inventory, decode_html,
    endpoint_labels, label_key, numbered_rows, render_outputs,
)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def numeric_length(value):
    """Parse a bare source number only; dashes/qualified portions stay unknown."""
    value = value.strip().replace('\ufeff', '')
    return float(value) if re.fullmatch(r'\d+(?:\.\d+)?', value) else None


def circuit_label(description):
    match = re.search(r'\bCkt\s*\.?\s*-?\s*(IV|III|II|I)\b', description, re.I)
    return match.group(1).upper() if match else None


def validate_circuits(document, nodes):
    known = {n['id'] for n in nodes['nodes']}
    ids = [r['id'] for r in document['circuits']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate circuit observation IDs')
    for row in document['circuits']:
        if len(row['endpoint_node_ids']) != 2 or not set(row['endpoint_node_ids']) <= known:
            raise ValueError('Invalid circuit endpoint reference')
        if row['endpoint_node_ids'][0] == row['endpoint_node_ids'][1]:
            raise ValueError('Unexpected self-loop requires reconciliation')
        if row['evidence_id'] not in document['evidence']:
            raise ValueError('Missing circuit provenance')
        if row['simulation_eligible'] or row['operational_status'] != 'unknown':
            raise ValueError('Unverified circuit must not enter simulation')
        if any(row[k] is not None for k in ['thermal_limit_mw', 'resistance_ohm', 'reactance_ohm', 'measured_flow_mw']):
            raise ValueError('Unverified electrical values must remain unknown')


def build_circuits(archive=DEFAULT_ARCHIVE, directory=DEFAULT_OUTPUT):
    # Rebuild the node inventory to prevent stale source/alias mappings being used.
    rules_bytes = (directory/'identity_rules.json').read_bytes()
    rebuilt = render_outputs(build_inventory(archive, json.loads(rules_bytes)), rules_bytes)
    for name, content in rebuilt.items():
        if (directory/name).read_text() != content:
            raise ValueError(f'Node inventory is stale: {name}')
    node_bytes = (directory/'nodes.json').read_bytes()
    nodes = json.loads(node_bytes)
    by_id = {n['id']: n for n in nodes['nodes']}
    registry = {}
    for node in nodes['nodes']:
        bind_alias(registry, node['name'], node['id'])
        for alias in node['aliases']:
            bind_alias(registry, alias['name'], node['id'])
    manifest_bytes = (archive/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    sources = {s['id']: s for s in manifest['sources']}
    rows, evidence, issues = [], {}, []

    def cite(source, locator, assertion):
        src = sources[source]
        if src['status'] != 'captured' or src['role'] == 'access_probe':
            raise ValueError(f'Not reference evidence: {source}')
        value = dict(source_id=source, source_sha256=src['sha256'], source_url=src['url'],
                     source_date=src['source_date'], retrieved_at=src['retrieved_at'],
                     locator=locator, assertion=assertion)
        identifier = 'cev-' + digest(json.dumps(value, sort_keys=True).encode())[:16]
        evidence[identifier] = value
        return identifier

    def add(source, serial, voltage, description, endpoints, label, locator, temporal_class,
            lengths=None, conductor=None, source_cells=None, alias_evidence=None):
        identifier = f'circuit-observation-{source.lower()}-{voltage}-{serial:03d}'
        ev = cite(source, locator, 'Dated source circuit row; endpoint order is presentation only, not flow direction. No current online status or thermal rating asserted.')
        row = dict(id=identifier, source_id=source, source_serial=serial, voltage_kv=voltage,
                   source_description=description, circuit_label=label, endpoint_node_ids=[e[1] for e in endpoints],
                   endpoint_source_labels=[e[0] for e in endpoints], direction='undirected',
                   temporal_class=temporal_class, identity_status='source_row_only',
                   source_reported_lengths=lengths, source_conductor=conductor, source_cells=source_cells,
                   historical_alias_evidence=alias_evidence or [], operational_status='unknown',
                   thermal_limit_mw=None, resistance_ohm=None, reactance_ohm=None, measured_flow_mw=None,
                   simulation_eligible=False, issue_ids=[], evidence_id=ev)
        rows.append(row)
        return row

    def issue(identifier, affected, reason, action):
        issues.append(dict(id=identifier, status='open', circuit_observation_ids=[r['id'] for r in affected],
                           reason=reason, required_evidence=action, evidence_ids=sorted({r['evidence_id'] for r in affected})))
        for row in affected:
            row['issue_ids'].append(identifier)

    for sid, voltage in [('SRC-03', 400), ('SRC-04', 220)]:
        text = decode_html((archive/sources[sid]['path']).read_bytes())[0]
        source_rows = numbered_rows(text, 1)
        for physical, serial, cells in source_rows:
            if len(cells) != 6:
                raise ValueError(f'Unexpected circuit table shape: {sid}:{serial}')
            bare = [numeric_length(v) for v in cells[2:5]]
            mixed = any(re.search(r'\bDTL\b|Powergrid', v, re.I) for v in cells[1:5])
            lengths = dict(overhead_source=cells[2], underground_source=cells[3], total_source=cells[4],
                           overhead_numeric_km=bare[0], underground_numeric_km=bare[1], total_numeric_km=bare[2],
                           scope='DTL portion or mixed owner qualification; not whole-route length' if mixed else 'as tabulated; whole-route extent unverified',
                           component_sum_status='not_comparable')
            if all(v is not None for v in bare):
                lengths['component_sum_status'] = 'matches' if abs(Decimal(cells[2])+Decimal(cells[3])-Decimal(cells[4])) <= Decimal('0.001') else 'mismatch'
            row = add(sid, serial, voltage, cells[1], endpoint_labels(cells[1], registry), circuit_label(cells[1]),
                      dict(table=1, physical_tr=physical, source_serial=serial), 'later_dtl_table', lengths, cells[5], cells)
            if not row['circuit_label']:
                issue(f'CIRCUIT-LABEL-{sid}-{serial}', [row], 'Source circuit suffix is absent/incomplete; a single circuit number is not inferred.', 'An official circuit/terminal identifier.')
            if any(by_id[n]['identity_status']=='unresolved_endpoint' for n in row['endpoint_node_ids']):
                issue(f'CIRCUIT-ENDPOINT-{sid}-{serial}', [row], 'At least one site identity is unresolved in the node register.', 'Resolve the linked Dwarka/Ballabhgarh node issue before electrical import.')
            if lengths['component_sum_status']=='mismatch':
                issue(f'LENGTH-{sid}-{serial}', [row], 'Numeric source components do not sum to the reported total.', 'Corroborating length record; retain source numbers unchanged.')
        expected_count = 14 if voltage == 400 else 115
        if [serial for _, serial, _ in source_rows] != list(range(1, expected_count + 1)):
            raise ValueError(f'Unexpected dated source serial coverage: {sid}')

    history_bytes = (directory/'historical_circuit_review.json').read_bytes()
    history = json.loads(history_bytes)
    if history['source_sha256'] != sources['SRC-01']['sha256']:
        raise ValueError('Historical review source fingerprint differs')
    historical_registry = dict(registry)
    for alias in history['source_qualified_aliases']:
        if alias['node_id'] not in by_id:
            raise ValueError('Historical alias references unknown node')
        bind_alias(historical_registry, alias['label'], alias['node_id'])
    actual = {(r['voltage_kv'], r['serial']) for r in history['rows']}
    expected = {(400,i) for i in range(1,13)} | {(220,i) for i in range(1,102)}
    if actual != expected or len(history['rows']) != 113:
        raise ValueError('Historical source row coverage differs from reviewed table')
    for spec in history['rows']:
        if spec['physical_page'] not in [31,32,33]:
            raise ValueError('Unexpected historical page')
        endpoints = endpoint_labels(spec['raw_description'], historical_registry)
        used_aliases = [alias for alias in history['source_qualified_aliases']
                        if label_key(alias['label']) in {label_key(e[0]) for e in endpoints}]
        add('SRC-01', spec['serial'], spec['voltage_kv'], spec['raw_description'],
            endpoints, spec['circuit_label'],
            dict(physical_page=spec['physical_page'], voltage_section_kv=spec['voltage_kv'], source_serial=spec['serial']),
            'historical_2019_table',
            dict(raw_extracted_line=spec['raw_extracted_line'], length_text=spec['length_text'],
                 scope='2019 tabulation; continuation cells not reconstructed; not a current route length'),
            alias_evidence=used_aliases)

    supplemental_bytes = (directory/'supplemental_connection_review.json').read_bytes()
    supplemental = json.loads(supplemental_bytes)
    if len(supplemental['reviewed_circuit_observations']) != 3:
        raise ValueError('Reviewed BBMB observation count differs')
    for spec in supplemental['reviewed_circuit_observations']:
        if spec['source_sha256'] != sources[spec['source_id']]['sha256']:
            raise ValueError('Supplemental connection source fingerprint differs')
        add(spec['source_id'], spec['review_serial'], spec['voltage_kv'], spec['description'],
            list(zip(spec['endpoint_source_labels'], spec['endpoint_node_ids'])), spec['circuit_label'],
            dict(physical_page=spec['physical_page'], section=spec['section'], review_serial=spec['review_serial']),
            'annual_report_2024_25', alias_evidence=[spec['note']])
    for claim in supplemental['reference_connection_claims']:
        if claim['source_sha256'] != sources[claim['source_id']]['sha256']:
            raise ValueError('Reference connection claim source fingerprint differs')
        claim['evidence_id'] = cite(claim['source_id'], dict(physical_page=claim['physical_page']), claim['note'])

    # Only compare identities within a dated source; repeated observations across years are not extra physical circuits.
    groups = defaultdict(list)
    for row in rows:
        key = (row['source_id'], row['voltage_kv'], tuple(sorted(row['endpoint_node_ids'])), row['circuit_label'])
        if row['circuit_label']:
            groups[key].append(row)
    for group in groups.values():
        if len(group)>1:
            issue('DUPLICATE-' + group[0]['id'], group, 'Same source, endpoint pair, voltage and circuit label occur more than once. Distinct physical circuits not established.', 'Independent terminal/circuit record; do not relabel or collapse observations automatically.')
    doc = dict(schema_version='1.0', scope=nodes['scope'], nodes_sha256=digest(node_bytes),
               source_manifest_sha256=digest(manifest_bytes), historical_review_sha256=digest(history_bytes),
               supplemental_review_sha256=digest(supplemental_bytes),
               assurance='Dated circuit observations, not a deduplicated/current operating graph.',
               circuits=rows, evidence=dict(sorted(evidence.items())))
    validate_circuits(doc, nodes)
    audit = audit_topology(nodes, doc, json.loads((directory/'unresolved.json').read_text()), issues, archive)
    audit['nodes_sha256'] = doc['nodes_sha256']
    audit['source_manifest_sha256'] = doc['source_manifest_sha256']
    audit['circuit_document_sha256'] = digest((json.dumps(doc, indent=2, ensure_ascii=False)+'\n').encode())
    audit['reference_connection_claim_ids'] = [c['id'] for c in supplemental['reference_connection_claims']]
    return {'circuits.json':doc, 'circuit_issues.json':dict(issues=issues), 'topology_audit.json':audit,
            'reference_connection_claims.json':supplemental}


def audit_topology(nodes, circuits, node_issues, circuit_issues, archive):
    """Assess a multigraph of observations without inventing links or declaring completeness."""
    latest = [r for r in circuits['circuits'] if r['temporal_class']=='later_dtl_table']
    historical = [r for r in circuits['circuits'] if r['temporal_class']=='historical_2019_table']
    adjacency = {n['id']: set() for n in nodes['nodes']}
    for row in latest:
        a,b = row['endpoint_node_ids']; adjacency[a].add(b); adjacency[b].add(a)
    seen, components = set(), []
    for start in sorted(adjacency):
        if start in seen: continue
        todo, component = [start], []
        while todo:
            node = todo.pop()
            if node in seen: continue
            seen.add(node); component.append(node); todo.extend(sorted(adjacency[node]-seen))
        components.append(sorted(component))
    def identity(row):
        return (row['voltage_kv'], tuple(sorted(row['endpoint_node_ids'])), row['circuit_label'])
    latest_keys = {identity(r) for r in latest}
    historical_only = [r['id'] for r in historical if identity(r) not in latest_keys]
    review = json.loads((archive/'review.json').read_text())
    return dict(
        schema_version='1.0', scope=nodes['scope'], audit_performed=True,
        integration_gate='not_passed', full_reference_completeness_verified=False,
        goal_50_verified_delhi_nodes_achieved=False, independently_verified_delhi_physical_site_count=None,
        inventory_record_count=len(nodes['nodes']), dated_circuit_observation_count=len(circuits['circuits']),
        later_table_rows_by_voltage=dict(Counter(str(r['voltage_kv']) for r in latest)),
        historical_table_rows_by_voltage=dict(Counter(str(r['voltage_kv']) for r in historical)),
        bbmb_report_circuit_observations=sum(r['source_id']=='SRC-13' for r in circuits['circuits']),
        source_row_coverage=dict(dtl_directory='47/47',later_circuit_tables='129/129',historical_circuit_tables='113/113',transformation_tables='46/46 retained; SOW unassigned'),
        later_endpoint_mentions=2*len(latest),
        later_rows_with_unresolved_endpoints=sum(any(n.startswith('candidate-') for n in r['endpoint_node_ids']) for r in latest),
        open_node_issue_ids=[i['id'] for i in node_issues['issues']],
        open_circuit_issue_ids=[i['id'] for i in circuit_issues],
        source_gap_ids=[i['id'] for i in review['open_items']],
        later_table_adjacency=dict(interpretation='Diagnostic of dated table observations including unresolved candidates; not an operating connectivity assessment.',
                                   connected_components=components, isolated_node_ids=sorted(n for n,neighbours in adjacency.items() if not neighbours)),
        historical_rows_without_exact_later_identity=historical_only,
        historical_comparison_note='A missing exact match can reflect spelling/identity, changed circuit labels, changed wiring or source coverage. It is not evidence of retirement. Matched rows do not establish unchanged lengths/status.',
        remaining_evidence_tasks=[
            dict(id='AUDIT-MAP-COVERAGE', sources=['SRC-01'], locators={'physical_pages':[29,30]},
                 task='Reconcile every in-scope historical ring/map connection and terminal against tables; map crossings are not junctions. External Dadri/Noida/Jhajjar and plant interfaces are not fully covered by DTL-owned tables.'),
            dict(id='AUDIT-BBMB-COVERAGE', sources=['SRC-01','SRC-13'], locators={'SRC-01_physical_pages':[33,35],'SRC-13_physical_pages':[82,86,87]},
                 task='Three named BBMB maintenance observations are recorded (Panipat–Narela III and Narela–Rohtak Road I/II). Confirm exact buses, full interface coverage and snapshot alignment before electrical import.'),
            dict(id='AUDIT-HISTORICAL-DIFFERENCES', sources=['SRC-01','SRC-03','SRC-04'],
                 task='Resolve the listed historical-only observations and source date/length conflicts without mixing snapshots.'),
            dict(id='AUDIT-TRANSFORMER-TERMINALS', sources=['SRC-05','SRC-06'],
                 task='Resolve SOW; define voltage-level buses and transformer terminal semantics. Site-level MVA observations are not inter-site transmission edges.'),
            dict(id='AUDIT-NODE-IDENTITY', sources=['SRC-01','SRC-02','SRC-04','SRC-13'],
                 task='Resolve the eight node issues, physical-site counting and Delhi geography. Do not claim the 50-node or 500+ scalability goals from record counts.'),
            dict(id='AUDIT-CIRCUIT-IDENTITY', sources=['SRC-03','SRC-04'],
                 task='Resolve duplicate/incomplete circuit labels and endpoint candidates; obtain independent current owner/terminal records.'),
        ],
        import_decision='Hold Step 7 electrical/model integration. Inventory review artifacts are usable; topology completeness is not established.',
        runtime_changed=False,
    )


def render(documents):
    rendered = {name:json.dumps(doc,indent=2,ensure_ascii=False)+'\n' for name,doc in documents.items()}
    stream=io.StringIO(newline=''); writer=csv.writer(stream,lineterminator='\n')
    columns=['id','source_id','source_serial','temporal_class','voltage_kv','circuit_label','endpoint_a','endpoint_b','source_description','operational_status','issue_ids']
    writer.writerow(columns)
    for row in documents['circuits.json']['circuits']:
        writer.writerow([row[k] for k in columns[:6]]+row['endpoint_node_ids']+[row['source_description'],row['operational_status'],';'.join(row['issue_ids'])])
    rendered['circuits.csv']=stream.getvalue()
    audit = documents['topology_audit.json']
    rows_by_id = {r['id']:r for r in documents['circuits.json']['circuits']}
    lines = [
        '# Delhi topology audit — Steps 5–6', '',
        '**Result: the topology acceptance gate has not passed.** The circuit inventory and',
        'audit are reviewable; completeness and electrical readiness remain unverified.', '',
        'This is the initial extraction audit. The later [identity review](RECONCILIATION.md)',
        'records dispositions for the six original node cases and corrects the report-count',
        'interpretation. Original findings stay preserved here; electrical readiness is separate.', '',
        '## Coverage reviewed', '',
        '| Evidence | Coverage |', '|---|---|',
        '| DTL station directory | 47/47 entries in the Step 4 node inventory |',
        '| Later DTL circuit tables | 129/129 rows: 14 at 400 kV, 115 at 220 kV |',
        '| June 2019 DTL circuit tables | 113/113 rows: 12 at 400 kV, 101 at 220 kV |',
        '| BBMB annual report 2024–25 | 3 named circuit observations on physical page 86 |',
        '| Total dated circuit observations | 245; not a count of distinct current lines |',
        '| Additional historical connection narratives | 7 claims retained separately; no inferred electrical edges |',
        '| Transformation tables | 46 observations retained; SOW remains unassigned |', '',
        'Source-byte hashes, source dates, retrieval times and row/page locators are in',
        '[circuits.json](circuits.json). [circuits.csv](circuits.csv) is the compact review list.',
        'The historical transcription and supplemental review inputs are pinned by hash.', '',
        '## Findings that prevent acceptance', '',
        '- Eight node identity/status issues remain in [unresolved.json](unresolved.json).',
        '- Twelve later DTL rows reference unresolved Dwarka or Ballabhgarh endpoint candidates.',
        '- Four later source labels omit a circuit number (SRC-04 rows 27, 40, 41 and 57).',
        '- SRC-04 rows 88 and 89 both state R.K. Puram–Trauma Centre Ckt-I. Both observations',
        '  are retained and flagged. No second circuit number or physical line is assumed.',
        '- Fifteen historical rows lack an exact endpoint/voltage/circuit-label match in',
        '  the later tables. Absence is not retirement evidence.',
        '- The 2019 map and external/plant terminals are not fully reconciled. DTL-owned',
        '  circuit tables cannot establish complete POWERGRID/BBMB/generation coverage.',
        '- Sources span different years. No single 2026 operating snapshot is established.',
        '- Coordinates, current status, MW limits, impedance and actual flows remain unknown.',
        '- 64 node records do not establish 50 distinct verified Delhi physical sites.', '',
        '## Nodes with no connection in the later DTL tables', '',
        'This is a source-coverage diagnostic, not evidence that the assets are disconnected',
        'in reality. BBMB observations and historical rows are kept outside this dated-table',
        'diagnostic rather than mixed into one apparent operating snapshot.', '',
    ]
    lines += [f'- `{node}`' for node in audit['later_table_adjacency']['isolated_node_ids']]
    lines += ['', '## Historical observations without an exact later match', '',
              '| Source row | Voltage | Historical label | Circuit |', '|---|---|---|---|']
    for identifier in audit['historical_rows_without_exact_later_identity']:
        row = rows_by_id[identifier]
        lines.append(f"| SRC-01 serial {row['source_serial']} | {row['voltage_kv']} kV | {row['source_description']} | {row['circuit_label']} |")
    lines += ['', '## Evidence needed before electrical/model integration', '']
    lines += [f"{i}. **{task['id']}** — {task['task']}" for i,task in enumerate(audit['remaining_evidence_tasks'],1)]
    lines += ['', 'The eight source-access/date/reuse gaps remain linked in [topology_audit.json](topology_audit.json).',
              'Resolving a source gap does not automatically close an asset/circuit issue.', '',
              '## Decision', '',
              'Hold Step 7 electrical/model integration until the above evidence is reconciled.',
              'No Neo4j import, runtime topology, dashboard, trained model or simulation was changed.',
              'Step 5 has a source-referenced inventory; full T03 verification is pending.',
              'Step 6 has an audit result; its completeness acceptance checkpoint remains open.', '',
              'Reproduce offline with matching original sources available:', '', '```bash',
              'python -m scripts.build_delhi_circuit_inventory --check',
              'python -m unittest discover -s tests -v', '```', '']
    rendered['AUDIT.md']='\n'.join(lines)
    return rendered


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,default=DEFAULT_ARCHIVE)
    parser.add_argument('--output-dir',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    documents=build_circuits(args.archive,args.output_dir)
    for name,content in render(documents).items():
        target=args.output_dir/name
        if args.check:
            if not target.exists() or target.read_text()!=content: raise ValueError(f'Stale output: {name}')
        else: target.write_text(content)
    audit=documents['topology_audit.json']
    print(json.dumps({k:audit[k] for k in ['dated_circuit_observation_count','later_table_rows_by_voltage','historical_table_rows_by_voltage','integration_gate']},indent=2))


if __name__=='__main__': main()
