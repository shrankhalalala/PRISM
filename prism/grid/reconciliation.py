"""Apply evidence-backed site identities without rewriting source observations."""

from copy import deepcopy
import hashlib
import json

from prism.config import ROOT


def apply_identity_review(payload, directory):
    review_bytes = (directory/'identity_resolution.json').read_bytes()
    review = json.loads(review_bytes)
    manifests = {}
    evidence = payload['node_evidence']

    def cite(spec):
        folder = spec['archive']
        if folder not in manifests:
            path = ROOT/'data/sources/delhi'/folder/'manifest.json'
            if not path.resolve().is_relative_to((ROOT/'data/sources/delhi').resolve()):
                raise ValueError('Evidence archive outside source directory')
            body=path.read_bytes()
            manifests[folder]=(json.loads(body),hashlib.sha256(body).hexdigest())
        source=next((s for s in manifests[folder][0]['sources'] if s['id']==spec['source_id']),None)
        if not source or source['status']!='captured' or source['sha256']!=spec['sha256']:
            raise ValueError('Identity review source checksum mismatch')
        if source['url']!=spec['url'] or source['retrieved_at']!=spec['retrieved_at'] or source['source_date']!=spec['source_date']:
            raise ValueError('Identity review source metadata differs')
        encoded=json.dumps(spec,sort_keys=True).encode()
        identifier='identity-ev-'+hashlib.sha256(encoded).hexdigest()[:20]
        evidence[identifier]=dict(spec,source_sha256=spec['sha256'])
        return identifier

    aliases={}
    resolved=[]
    decisions=[]
    assets={a['id']:a for a in payload['assets']}
    for decision in review['identity_resolutions']:
        item=deepcopy(decision)
        item['evidence_ids']=[cite(e) for e in item['evidence']]
        resolved.append(item['issue_id']);decisions.append(item)
        if item['decision']=='merge_reference_identity':
            old,new=item['merged_id'],item['canonical_id']
            if old not in assets or new not in assets or old==new or old in aliases:
                raise ValueError('Invalid reviewed identity merge')
            aliases[old]=new
            target=assets[new]
            source=assets.pop(old)
            target.setdefault('merged_source_records',[]).append(source)
            target.setdefault('merged_inventory_ids',[]).append(old)
            target['evidence_ids']=sorted(set(target['evidence_ids']+source['evidence_ids']+item['evidence_ids']))
            target['aliases'].append(dict(name=source['name'],status='corroborated_reference_identity',evidence_ids=item['evidence_ids']))
            for field in ['voltage_assertions','ownership_assertions','transformation_observations','historical_status_assertions']:
                target[field].extend(source[field])
            target['identity_status']='corroborated_reference_identity'
    if set(aliases.values()) & aliases.keys():
        raise ValueError('Identity chains must be reconciled explicitly')
    for spec in review['new_assets']:
        if spec['id'] in assets:raise ValueError('Duplicate reviewed asset')
        ev=cite(spec['evidence'])
        assets[spec['id']]=dict(id=spec['id'],name=spec['name'],kind='substation',scope_role='documented_direct_boundary_interface',boundary_classification=spec['boundary'],identity_status='source_corroborated',operational_status='unknown',latitude=None,longitude=None,current_output_mw=None,available_capacity_mw=None,simulation_eligible=False,aliases=[],ownership_assertions=[dict(owner=spec['owner'],evidence_id=ev)],voltage_assertions=[dict(levels_kv=[spec['voltage_kv']],status='source_reported',evidence_id=ev)],transformation_observations=[],historical_status_assertions=[],evidence_ids=[ev],issue_ids=[],notes=[])
    assets['ss-dwarka-sector-5']['site_voltage_levels_kv']=[220,400]
    assets['ss-dwarka-sector-5']['voltage_owner_note']='400/220 kV ISTS complex with DTL lower-voltage scheme; 66 kV additions remain date-qualified.'
    dwarka=next(d for d in decisions if d['issue_id']=='IDENTITY-CANDIDATE-DWARKA')
    assets['ss-dwarka-sector-5']['ownership_assertions'].append(dict(owner='POWERGRID',scope='historical 400 kV ISTS portion; 220 kV and below ownership separately attributed to DTL',evidence_id=dwarka['evidence_ids'][-1]))
    assets['ss-budella']['reference_classification']='planned_as_of_2025_06_25'
    assets['ss-budella']['counts_toward_existing_coverage']=False
    assets['ss-budella']['historical_status_assertions'].append(dict(status='under_tendering; tentative FY2028-29 commissioning',as_of='2025-06-25',evidence_ids=next(d['evidence_ids'] for d in decisions if d['issue_id']=='NODE-BUDELLA-STATUS')))
    for identifier in ['ss-narela-dtl','ss-narela-bbmb']:
        assets[identifier]['reference_site_group']='narela-extended-bus-complex'
    for identifier in ['plant-gtps','plant-pps1','plant-pps3-bawana','ss-narela-bbmb']:
        assets[identifier]['boundary_classification']='internal'
    assets['plant-jhajjar']['name']='Jhajjar (APCL) generation interface'
    assets['plant-jhajjar']['boundary_classification']='external_boundary'
    assets['plant-jhajjar']['reference_owner']='APCL'
    resolved_all=set(resolved)|set(payload['resolved_metadata_issue_ids'])
    for asset in assets.values():
        asset['open_issue_ids']=[i for i in asset.get('issue_ids',[]) if i not in resolved_all]
        asset['resolved_reference_issue_ids']=[i for i in asset.get('issue_ids',[]) if i in resolved_all]
    for circuit in payload['circuit_observations']:
        original=list(circuit['endpoint_node_ids'])
        circuit['endpoint_node_ids']=[aliases.get(n,n) for n in original]
        if original!=circuit['endpoint_node_ids']:
            circuit['source_endpoint_node_ids']=original
            circuit['identity_resolution_ids']=[d['issue_id'] for d in decisions if d.get('merged_id') in original]
        circuit['open_issue_ids']=[i for i in circuit['issue_ids'] if not i.startswith('CIRCUIT-ENDPOINT-')]
    endpoint_issue_ids=[i['id'] for i in payload['circuit_issues'] if i['id'].startswith('CIRCUIT-ENDPOINT-')]
    payload['circuit_issue_resolutions']={identifier:'Endpoint remapped by reviewed Dwarka/Ballabhgarh identity evidence; original source warning preserved.' for identifier in endpoint_issue_ids}
    interfaces=[]
    for spec in review['interfaces']:
        record=deepcopy(spec)
        record['evidence_ids']=[cite(e) for e in spec['evidence']]
        record['direction']='undirected'
        record['assertion_only']=True
        if not set(record['endpoint_node_ids'])<=assets.keys():raise ValueError('Interface endpoint missing')
        interfaces.append(record)
    represented=review['map_review']['represented_asset_ids']
    if len(set(represented))!=len(represented) or not set(represented)<=assets.keys():
        raise ValueError('Map asset coverage has invalid/duplicate IDs')
    map_evidence=cite(review['map_review']['evidence'])
    if {e['observation_id'] for e in review['historical_changes']['entries']}!=set(payload['audit']['historical_rows_without_exact_later_identity']):
        raise ValueError('Historical difference register is incomplete')
    historical_evidence=[cite(e) for e in review['historical_changes']['evidence']]
    directory_rules=json.loads((directory/'identity_rules.json').read_text())
    minimum_ids=[s['id'] for s in directory_rules['directory']]+['plant-gtps','plant-pps1','plant-pps3-bawana']
    if len(set(minimum_ids))!=50 or not set(minimum_ids)<=assets.keys():
        raise ValueError('Report coverage needs 47 directory assets and three identified plants')
    if any(assets[n]['kind'] not in {'plant','substation'} or assets[n]['boundary_classification']!='internal' for n in minimum_ids):
        raise ValueError('Minimum coverage must be supported Delhi substation/plant identities')
    payload.update(assets=sorted(assets.values(),key=lambda a:a['id']),topology_interfaces=interfaces,
                   identity_resolution=dict(review=review,decisions=decisions,aliases=aliases,review_sha256=hashlib.sha256(review_bytes).hexdigest()),
                   resolved_reference_issue_ids=sorted(resolved),remaining_node_issue_ids=[],
                   topology_coverage=dict(reference_identity_issues_closed=sorted(resolved),unresolved_original_node_issue_ids=[],
                     source_referenced_delhi_asset_count=len(minimum_ids),counted_delhi_asset_ids=sorted(minimum_ids),
                     physical_site_count=None,report_count_requirement='50 Delhi substation/plant nodes; no claim of 50 geographically separate sites',
                     map_asset_record_count=len(represented),map_asset_ids=represented,map_evidence_id=map_evidence,
                     canonical_assets=len(assets),source_node_records=len(payload['assets']),aliases_removed_from_canonical_count=aliases,
                     dated_circuit_observations=len(payload['circuit_observations']),source_directory_rows=47,
                     field_questions=review['field_questions'],complete_current_operating_network_verified=False,
                     electrical_simulation_ready=False))
    payload['topology_coverage']['historical_comparison_findings_accounted']=len(review['historical_changes']['entries'])
    payload['topology_coverage']['historical_comparison_evidence_ids']=historical_evidence
    payload['topology_coverage']['endpoint_issue_ids_reconciled']=endpoint_issue_ids
    payload['topology_coverage']['identity_gate']='resolved_for_declared_site_level_reference_model'
    payload['node_issue_register_scope']='Initial extraction issues are preserved; identity_resolution and remaining_node_issue_ids give current dispositions.'
    payload['circuit_issue_register_scope']='Initial source warnings are preserved; circuit_issue_resolutions and per-observation open_issue_ids give reviewed dispositions.'
    payload['identity_resolution']['manifest_sha256']={folder:checksum for folder,(_,checksum) in sorted(manifests.items())}
    # The initial audit stays immutable; the current acceptance result is separate.
    payload['remaining_node_issue_ids']=[i['id'] for i in payload['node_issues'] if i['id'] not in resolved_all]
    return payload
