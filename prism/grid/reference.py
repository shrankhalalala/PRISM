"""Versioned, non-operational reference graph; independent of simulation fixtures."""

import hashlib
import json
from pathlib import Path
import re

import networkx as nx

from prism.config import ROOT
from prism.grid.reconciliation import apply_identity_review

DIRECTORY = ROOT / 'data/topology/delhi'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def build_reference(directory=DIRECTORY):
    """Package reviewed evidence without promoting it to an operating snapshot."""
    directory = Path(directory)
    read = lambda name: json.loads((directory/name).read_text())
    nodes, circuits, audit = read('nodes.json'), read('circuits.json'), read('topology_audit.json')
    if hashlib.sha256((directory/'nodes.json').read_bytes()).hexdigest() != circuits['nodes_sha256']:
        raise ValueError('Node inventory fingerprint mismatch')
    if hashlib.sha256((directory/'circuits.json').read_bytes()).hexdigest() != audit['circuit_document_sha256']:
        raise ValueError('Circuit audit fingerprint mismatch')
    review = read('reconciliation_review.json')
    archive = ROOT/'data/sources/delhi'/review['supplemental_archive']
    manifest_bytes = (archive/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    sources = {s['id']:s for s in manifest['sources']}
    for claim in review['conclusions']:
        source = sources.get(claim['source_id'])
        if not source or source['status'] != 'captured' or source['sha256'] != claim['source_sha256']:
            raise ValueError('Reconciliation evidence fingerprint mismatch')
    resolved = {c['issue_id'] for c in review['conclusions'] if c['status']=='resolved_metadata_only'}
    node_issues = read('unresolved.json')['issues']
    assets = nodes['nodes']
    asset_map = {asset['id']:asset for asset in assets}
    for asset in assets:
        asset['open_issue_ids'] = [i for i in asset['issue_ids'] if i not in resolved]
        asset['resolved_metadata_issue_ids'] = [i for i in asset['issue_ids'] if i in resolved]
        asset['reconciliation_ids'] = [c['id'] for c in review['conclusions'] if asset['id'] in c['node_ids']]
    for claim in review['conclusions']:
        effect = claim['effect']
        if claim['id']=='REC-TIMARPUR':
            asset_map['ss-timarpur']['corroborated_nominal_voltage_kv'] = effect['nominal_voltage_kv']
        if claim['id']=='REC-SOW':
            observation = next(r for r in read('transformation_mentions.json')['observations']
                               if r['source_id']=='SRC-06' and r['source_serial']==35)
            observation.update(node_id=effect['assigned_node_id'], reconciliation_id=claim['id'])
            asset_map[effect['assigned_node_id']]['transformation_observations'].append(observation)
        for circuit in circuits['circuits']:
            if circuit['source_id']==effect.get('source_id') and circuit['source_serial'] in effect.get('source_serials',[]):
                circuit['source_declared_multiplicity'] = effect['source_declared_multiplicity']
                circuit.setdefault('reconciliation_ids',[]).append(claim['id'])
    result = dict(schema_version='1.0', mode='reference_only', scope=nodes['scope'],
                  assurance='Dated source observations; not a verified operating grid or simulation input.',
                  simulation_eligible=False, electrical_integration_gate='not_passed',
                  assets=assets, circuit_observations=circuits['circuits'],
                  node_evidence=nodes['evidence'], circuit_evidence=circuits['evidence'],
                  reference_claims=read('reference_connection_claims.json'),
                  audit=audit, node_issues=node_issues, circuit_issues=read('circuit_issues.json')['issues'],
                  reconciliation=review,
                  reconciliation_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                  resolved_metadata_issue_ids=sorted(resolved),
                  remaining_node_issue_ids=sorted(i['id'] for i in node_issues if i['id'] not in resolved))
    result = apply_identity_review(result, directory)
    result['content_sha256'] = fingerprint(result)
    result['dataset'] = 'delhi_reference_' + result['content_sha256']
    validate_reference(result)
    return result


def validate_reference(payload):
    """Validate an undirected multigraph of evidence, allowing unknowns and islands."""
    if payload.get('schema_version') != '1.0' or payload.get('mode') != 'reference_only':
        raise ValueError('Expected a reference-only dataset')
    if payload.get('simulation_eligible') is not False or payload.get('electrical_integration_gate') != 'not_passed':
        raise ValueError('Reference data cannot certify electrical readiness')
    body = {k:v for k,v in payload.items() if k not in {'dataset','content_sha256'}}
    checksum = fingerprint(body)
    if payload.get('content_sha256') != checksum or payload.get('dataset') != 'delhi_reference_'+checksum:
        raise ValueError('Reference dataset fingerprint mismatch')
    if not re.fullmatch(r'delhi_reference_[0-9a-f]{64}', payload['dataset']):
        raise ValueError('Invalid reference dataset namespace')
    graph = nx.MultiGraph()
    if not payload.get('assets'):
        raise ValueError('Reference assets are required')
    for asset in payload['assets']:
        identifier = asset.get('id')
        if not isinstance(identifier,str) or not identifier or identifier in graph:
            raise ValueError('Reference asset IDs must be unique nonempty strings')
        if asset.get('kind') not in {'substation','plant','unresolved_asset'}:
            raise ValueError('Invalid reference asset kind')
        if asset.get('simulation_eligible') is not False or asset.get('operational_status') != 'unknown':
            raise ValueError('Unverified asset operating status')
        if any(asset.get(k) is not None for k in ['available_capacity_mw','current_output_mw','latitude','longitude']):
            raise ValueError('Unverified asset measurements')
        if not asset.get('evidence_ids') or not set(asset['evidence_ids']) <= payload['node_evidence'].keys():
            raise ValueError('Missing asset evidence')
        graph.add_node(identifier, **asset)
    ids=set()
    for circuit in payload['circuit_observations']:
        identifier = circuit.get('id')
        ends = circuit.get('endpoint_node_ids',[])
        if not isinstance(identifier,str) or not identifier or identifier in ids or identifier in graph.nodes:
            raise ValueError('Circuit observation IDs must be unique')
        if len(ends)!=2 or any(n not in graph for n in ends) or ends[0]==ends[1]:
            raise ValueError('Invalid reference endpoints')
        if circuit.get('direction') != 'undirected' or circuit.get('simulation_eligible') is not False or circuit.get('operational_status') != 'unknown':
            raise ValueError('Unverified circuit operating semantics')
        if any(circuit.get(k) is not None for k in ['thermal_limit_mw','resistance_ohm','reactance_ohm','measured_flow_mw']):
            raise ValueError('Unverified circuit parameters')
        if circuit.get('evidence_id') not in payload['circuit_evidence']:
            raise ValueError('Missing circuit evidence')
        if circuit.get('voltage_kv') not in {220,400}:
            raise ValueError('Unsupported reference circuit voltage')
        ids.add(identifier)
        graph.add_edge(*ends,key=identifier,**circuit)
    for interface in payload.get('topology_interfaces',[]):
        identifier=interface.get('id')
        ends=interface.get('endpoint_node_ids',[])
        if not isinstance(identifier,str) or not identifier or identifier in ids or identifier in graph:
            raise ValueError('Interface assertion ID must be unique')
        if len(ends)!=2 or not set(ends)<=graph.nodes.keys() or ends[0]==ends[1]:
            raise ValueError('Invalid interface endpoints')
        if interface.get('assertion_only') is not True or interface.get('simulation_eligible') is not False or interface.get('operational_status')!='unknown':
            raise ValueError('Interface assertion cannot certify operating state')
        if not interface.get('evidence_ids') or not set(interface['evidence_ids'])<=payload['node_evidence'].keys():
            raise ValueError('Interface evidence missing')
        if interface.get('voltage_kv') not in {220,400} or any(interface.get(k) is not None for k in ['thermal_limit_mw','resistance_ohm','reactance_ohm','measured_flow_mw']):
            raise ValueError('Unverified interface electrical parameters')
        ids.add(identifier)
        graph.add_edge(*ends,key=identifier,**interface)
    return graph
