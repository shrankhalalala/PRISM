"""Validate/export or explicitly import a non-operational Delhi reference snapshot."""

import argparse
import csv
import json
import os
from pathlib import Path

from prism.grid.reference import DIRECTORY, build_reference


def write_review(payload, directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'reference_assets.csv').open('w',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['id','name','kind','boundary','classification','site_group','merged_inventory_ids','current_status'])
        for asset in payload['assets']:
            writer.writerow([asset['id'],asset['name'],asset['kind'],asset['boundary_classification'],asset.get('reference_classification','source_referenced'),asset.get('reference_site_group',''),';'.join(asset.get('merged_inventory_ids',[])),asset['operational_status']])
    coverage=payload['topology_coverage']
    (directory/'reconciled_coverage.json').write_text(json.dumps(coverage,indent=2,ensure_ascii=False)+'\n')
    lines=['# Corrected topology identity review','',
           'The six original node discrepancies have documented dispositions for a site-level reference model.',
           'This is distinct from a fully verified current switching or electrical simulation model.','',
           f"Canonical assets: **{len(payload['assets'])}**. Dated circuit observations: **{len(payload['circuit_observations'])}**.",
           f"Additional interface/section assertions: **{len(payload['topology_interfaces'])}**; these are not additional confirmed physical circuits.",'',
           '## Decisions','']
    for decision in payload['identity_resolution']['decisions']:
        lines += [f"### {decision['issue_id']}",'',decision['finding'],'']
        for source in decision['evidence']:
            lines.append(f"- [{source['source_id']}]({source['url']}), locator: `{json.dumps(source['locator'],ensure_ascii=False)}`")
        lines.append('')
    lines += ['## Coverage and counting','',
              'Review III physical pages 2 and 11 require 50 Delhi substation/plant nodes. Our earlier requirement for 50 geographically separate sites was stricter than the report and is corrected.',
              'The count is 47 directory asset identities plus GTPS, PPS-I and PPS-III. It excludes the extra BBMB Narela owner portion, aliases, planned Budella and external assets. Plant/substation identities may share a complex; no count of 50 separate geographic sites is asserted.','',
              f"The June 2019 schematic is reconciled to {coverage['map_asset_record_count']} asset/owner-section records; Narela has two portions under one map symbol. The original 15 historical identity differences are accounted for as aliases, single-circuit label omissions or documented LILO changes. Source length conflicts remain preserved.",'',
              'The original node/circuit extraction and initial audit remain unchanged. Corrected records are in [reference_assets.csv](reference_assets.csv), with [coverage](reconciled_coverage.json) and the full [versioned dataset](reference_dataset.json).','',
              '## Remaining limits','']
    lines += [f"- **{q['id']}**: {q['reason']}" for q in coverage['field_questions']]
    lines += ['', 'The 50-node source-reference coverage target is represented. Complete current network coverage, current electrical state and simulation readiness are not established by that count.',
              'No website/model/telemetry update is included in this reconciliation.','',f"Dataset: `{payload['dataset']}`",'']
    (directory/'RECONCILIATION.md').write_text('\n'.join(lines))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',type=Path,default=DIRECTORY)
    parser.add_argument('--output',type=Path,help='Save reviewable versioned reference JSON')
    parser.add_argument('--review-dir',type=Path,help='Write corrected asset CSV, coverage JSON and readable reconciliation')
    parser.add_argument('--import-neo4j',action='store_true',help='Import immutable evidence dataset; never simulation LINE data')
    args=parser.parse_args()
    payload=build_reference(args.inventory)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    if args.review_dir:write_review(payload,args.review_dir)
    counts=dict(dataset=payload['dataset'],mode=payload['mode'],assets=len(payload['assets']),circuit_observations=len(payload['circuit_observations']),interface_assertions=len(payload.get('topology_interfaces',[])),source_referenced_delhi_assets=payload['topology_coverage']['source_referenced_delhi_asset_count'],resolved_metadata_issues=payload['resolved_metadata_issue_ids'],resolved_reference_issues=payload['resolved_reference_issue_ids'],remaining_node_issues=payload['remaining_node_issue_ids'],electrical_integration_gate=payload['electrical_integration_gate'])
    if args.import_neo4j:
        password=os.environ.get('NEO4J_PASSWORD')
        if not password: raise SystemExit('Export NEO4J_PASSWORD before import.')
        from prism.grid.reference_store import Neo4jReferenceStore
        store=Neo4jReferenceStore(os.environ.get('NEO4J_URI','bolt://localhost:7687'),os.environ.get('NEO4J_USER','neo4j'),password)
        try: counts['neo4j']=store.seed(payload)
        finally: store.close()
    print(json.dumps(counts,indent=2))


if __name__=='__main__': main()
