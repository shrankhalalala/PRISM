"""Labeled 600-node fixture, independent namespace and real Neo4j repeat-import checks."""
from copy import deepcopy
import json
import os
from pathlib import Path
from time import perf_counter
from prism.grid.model import validate_grid
from prism.grid.neo4j_store import Neo4jStore


def fixture():
    nodes=[dict(id=f'scale-{i:03}',name=f'Synthetic scale asset {i:03}',kind='substation',status='online',voltage_kv=220,
        x=50+(i%30)*28,y=50+(i//30)*28) for i in range(600)]
    edges=[dict(id=f'scale-edge-{i:04}',source=f'scale-{a:03}',target=f'scale-{b:03}',capacity_mw=100,status='online')
        for i,(a,b) in enumerate([(i,(i+1)%600) for i in range(600)]+[(i,(i+30)%600) for i in range(600)])]
    return dict(schema_version='1.0',data_source='synthetic_scalability_fixture',description='Fictional 600-node scaling fixture; not Delhi inventory or physical operating data.',nodes=nodes,edges=edges)


def view_fixture(grid):
    from prism.grid.presentation import reference_view
    from prism.config import ROOT
    original=reference_view(ROOT/'data/topology/delhi/reference_dataset.json');data=deepcopy(original)
    base=original['assets'][0];data['assets']=[]
    for node in grid['nodes']:
        asset=deepcopy(base);asset.update(id=node['id'],name=node['name'],kind='substation',aliases=[],evidence_ids=[],merged_inventory_ids=[],
            layout=dict(x=node['x'],y=node['y']),operational_status='synthetic_fixture',reference_classification='synthetic_scalability_fixture')
        data['assets'].append(asset)
    base=original['connections'][0];data['connections']=[]
    for edge in grid['edges']:
        connection=deepcopy(base);connection.update(id=edge['id'],source=edge['source'],target=edge['target'],source_id='SYNTHETIC SCALABILITY FIXTURE',
            evidence_ids=[],issue_ids=[],circuit_label=edge['id'],temporal_class='synthetic_fixture',assertion_only=False,detail='Fictional scaling connection; not Delhi evidence.')
        data['connections'].append(connection)
    data.update(dataset='synthetic_scale_600',evidence={},coverage={'source_referenced_delhi_asset_count':0,'field_questions':[{'id':'synthetic-only','reason':'600-node test fixture; not Delhi coverage.'}]})
    return data


def main():
    grid=fixture();start=perf_counter();validate_grid(grid);validation=perf_counter()-start
    Path('artifacts').mkdir(exist_ok=True);Path('artifacts/scalability600.json').write_text(json.dumps(grid));Path('artifacts/scalability600-view.json').write_text(json.dumps(view_fixture(grid)))
    store=Neo4jStore(os.environ.get('NEO4J_URI','bolt://127.0.0.1:7687'),os.environ.get('NEO4J_USER','neo4j'),os.environ['NEO4J_PASSWORD'])
    try:
        with store.driver.session() as session:
            before=[tuple(r.values()) for r in session.run("MATCH (n:PrismReferenceEntity) RETURN n.dataset AS dataset,count(n) AS nodes ORDER BY dataset")]
        start=perf_counter();first=store.seed(grid,'prism_scale600_synthetic');import_seconds=perf_counter()-start;second=store.seed(grid,'prism_scale600_synthetic')
        with store.driver.session() as session:
            after=[tuple(r.values()) for r in session.run("MATCH (n:PrismReferenceEntity) RETURN n.dataset AS dataset,count(n) AS nodes ORDER BY dataset")]
            start=perf_counter();count=session.run("MATCH (n:PrismNode {dataset:'prism_scale600_synthetic'})-[:LINE]-(m) RETURN count(DISTINCT n) AS nodes,count(DISTINCT m) AS neighbors").single();query_seconds=perf_counter()-start
        assert first==second=={'nodes':600,'edges':1200} and before==after and count['nodes']==600
        result=dict(data_source='synthetic_scalability_fixture',nodes=600,edges=1200,validation_seconds=validation,first_import_seconds=import_seconds,
            query_seconds=query_seconds,repeat_import_equal=True,reference_namespace_counts_preserved=True,
            limitation='600-node synthetic import/query and separate browser-render fixture; does not increase Delhi inventory or validate electrical models.')
        Path('reports/phase3_scalability.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:store.close()

if __name__=='__main__':main()
