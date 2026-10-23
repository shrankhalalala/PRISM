"""Choose the validated local export or an independently verified Neo4j snapshot."""
from functools import lru_cache
import json
import os
from time import time
from prism.config import ROOT
from prism.grid.presentation import reference_view
from prism.grid.reference_store import Neo4jReferenceStore
from prism.grid.reference import validate_reference


@lru_cache(maxsize=2)
def _database_view(dataset):
    store=Neo4jReferenceStore(os.environ['NEO4J_URI'],os.environ.get('NEO4J_USER','neo4j'),os.environ['NEO4J_PASSWORD'])
    try:
        with store.driver.session() as session:
            row=session.run('MATCH (d:PrismReferenceDataset {dataset:$dataset}) RETURN d.payload_json AS payload',dataset=dataset).single()
            if row is None:raise OSError('Reference dataset missing in Neo4j')
            payload=json.loads(row['payload'])
        validate_reference(payload)
        if payload['dataset']!=dataset:raise OSError('Reference dataset version mismatch')
        store.verify(payload)
        edges=[]
        for row in payload['circuit_observations']+payload.get('topology_interfaces',[]):
            edges.append(dict(source=row['endpoint_node_ids'][0],target=row['endpoint_node_ids'][1],
                temporal_class=row.get('temporal_class','interface_assertion'),
                evidence_ids=row.get('evidence_ids',[row.get('evidence_id')])))
        return dict(dataset=dataset,assets=payload['assets'],connections=edges,source_store='neo4j_verified_snapshot')
    except Exception as exc:
        raise OSError('Verified Neo4j diagnostic input unavailable') from exc
    finally:store.close()


def diagnostic_view():
    local=reference_view(ROOT/'data/topology/delhi/reference_dataset.json')
    if os.environ.get('PRISM_DIAGNOSIS_STORE')=='neo4j':return _database_view(local['dataset'])
    return dict(local,source_store='validated_local_export')
