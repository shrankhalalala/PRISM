"""Read-only presentation of a validated, source-dated reference export."""

from functools import lru_cache
import json
from pathlib import Path

import networkx as nx

from prism.grid.reference import validate_reference


@lru_cache(maxsize=4)
def _load(path, modified_ns, size):
    payload=json.loads(Path(path).read_text())
    graph=validate_reference(payload)
    # Pack components separately: an isolated asset must not squeeze the whole network.
    simple=nx.Graph(graph)
    components=sorted(nx.connected_components(simple),key=lambda c:(-len(c),sorted(c)))
    main=components[0]
    raw=nx.spring_layout(simple.subgraph(main),seed=42,k=.28,iterations=300,scale=1)
    xs=[float(p[0]) for p in raw.values()];ys=[float(p[1]) for p in raw.values()]
    width=760 if len(components)>1 else 880
    positions={identifier:dict(x=50+(float(point[0])-min(xs))/max(max(xs)-min(xs),.001)*width,
                              y=50+(float(point[1])-min(ys))/max(max(ys)-min(ys),.001)*590)
               for identifier,point in raw.items()}
    remaining=sorted(set(simple)-main)
    for index,identifier in enumerate(remaining):
        positions[identifier]=dict(x=920+(index//8)*50,y=90+(index%8)*70)
    assets=[]
    for asset in payload['assets']:
        point=positions[asset['id']]
        assets.append(dict(asset,layout={k:round(v,3) for k,v in point.items()}))
    evidence={}
    for identifier,entry in {**payload['node_evidence'],**payload['circuit_evidence']}.items():
        evidence[identifier]=dict(source_id=entry['source_id'],url=entry.get('url',entry.get('source_url')),
                                  source_date=entry.get('source_date'),locator=entry.get('locator'),
                                  source_sha256=entry.get('source_sha256',entry.get('sha256')))
    connections=[]
    for row in payload['circuit_observations']:
        source=evidence[row['evidence_id']]
        connections.append(dict(id=row['id'],source=row['endpoint_node_ids'][0],target=row['endpoint_node_ids'][1],
            kind='circuit_observation',voltage_kv=row['voltage_kv'],circuit_label=row['circuit_label'],
            source_id=row['source_id'],source_date=source['source_date'],temporal_class=row['temporal_class'],
            detail=row['source_description'],issue_ids=row.get('open_issue_ids',row['issue_ids']),
            evidence_ids=[row['evidence_id']],operational_status='unknown',assertion_only=False))
    for row in payload.get('topology_interfaces',[]):
        primary=evidence[row['evidence_ids'][0]]
        connections.append(dict(id=row['id'],source=row['endpoint_node_ids'][0],target=row['endpoint_node_ids'][1],
            kind=row['kind'],voltage_kv=row['voltage_kv'],circuit_label=None,
            source_id=primary['source_id'],source_date=primary['source_date'],temporal_class='interface_assertion',
            detail=row['detail'],issue_ids=[],evidence_ids=row['evidence_ids'],operational_status='unknown',assertion_only=True))
    return dict(dataset=payload['dataset'],mode='reference_only',assurance=payload['assurance'],
                coverage=payload['topology_coverage'],assets=assets,connections=connections,evidence=evidence,
                layout_assurance='Deterministic schematic positions; not geographic coordinates or simulated power flows.')


def reference_view(path):
    path=Path(path)
    stat=path.stat()
    return _load(str(path.resolve()),stat.st_mtime_ns,stat.st_size)
