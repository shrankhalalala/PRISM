"""Immutable Neo4j evidence snapshots, isolated from PrismNode/LINE simulation data."""

from prism.grid.reference import canonical, validate_reference


def entity_rows(payload):
    """Encode nested source records as JSON, preserving unknowns and provenance."""
    assets = [dict(id=a['id'], entity_type='asset', record_json=canonical(a)) for a in payload['assets']]
    circuits = [dict(id=c['id'], entity_type='circuit_observation', record_json=canonical(c))
                for c in payload['circuit_observations']]
    interfaces = [dict(id=c['id'], entity_type='interface_assertion', record_json=canonical(c))
                  for c in payload.get('topology_interfaces',[])]
    endpoints = [dict(circuit_id=c['id'], asset_id=a, position=position)
                 for c in payload['circuit_observations']+payload.get('topology_interfaces',[])
                 for position,a in enumerate(c['endpoint_node_ids'],1)]
    return assets+circuits+interfaces, endpoints


class Neo4jReferenceStore:
    """Append a content-addressed reference dataset; never delete or replace datasets."""

    def __init__(self, uri, user, password):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user,password), connection_timeout=5)

    def close(self):
        self.driver.close()

    def seed(self, payload):
        validate_reference(payload)
        with self.driver.session() as session:
            session.run('CREATE CONSTRAINT prism_reference_dataset IF NOT EXISTS FOR (d:PrismReferenceDataset) REQUIRE d.dataset IS UNIQUE').consume()
            session.run('CREATE CONSTRAINT prism_reference_entity IF NOT EXISTS FOR (n:PrismReferenceEntity) REQUIRE (n.dataset,n.id) IS UNIQUE').consume()
            return session.execute_write(self._write, payload)

    @staticmethod
    def _write(tx, payload):
        dataset = payload['dataset']
        encoded = canonical(payload)
        existing = tx.run('MATCH (d:PrismReferenceDataset {dataset:$dataset}) RETURN properties(d) AS props',dataset=dataset).single()
        if existing:
            if existing['props'].get('payload_json') != encoded:
                raise ValueError('Existing immutable dataset differs; refusing to overwrite')
        else:
            # Reject orphan entities rather than adopting or deleting unrelated records.
            count = tx.run('MATCH (n:PrismReferenceEntity {dataset:$dataset}) RETURN count(n) AS count',dataset=dataset).single()['count']
            if count:
                raise ValueError('Namespace contains orphan records; refusing to overwrite')
            entities, endpoints = entity_rows(payload)
            tx.run('CREATE (d:PrismReferenceDataset {dataset:$dataset, payload_json:$payload, mode:"reference_only"})',dataset=dataset,payload=encoded).consume()
            tx.run('UNWIND $rows AS row CREATE (n:PrismReferenceEntity) SET n = row, n.dataset = $dataset',rows=entities,dataset=dataset).consume()
            tx.run('UNWIND $rows AS row MATCH (c:PrismReferenceEntity {dataset:$dataset,id:row.circuit_id}), (a:PrismReferenceEntity {dataset:$dataset,id:row.asset_id}) CREATE (c)-[:REFERENCE_ENDPOINT {position:row.position}]->(a)',rows=endpoints,dataset=dataset).consume()
        return Neo4jReferenceStore._verify(tx,payload)

    def verify(self, payload):
        validate_reference(payload)
        with self.driver.session() as session:
            return session.execute_read(self._verify,payload)

    @staticmethod
    def _verify(tx,payload):
        dataset=payload['dataset']
        root = tx.run('MATCH (d:PrismReferenceDataset {dataset:$dataset}) RETURN properties(d) AS props',dataset=dataset).single()
        if not root or root['props'] != dict(dataset=dataset,payload_json=canonical(payload),mode='reference_only'):
            raise ValueError('Stored dataset metadata differs')
        expected_entities, expected_endpoints = entity_rows(payload)
        actual = [dict(r['props']) for r in tx.run('MATCH (n:PrismReferenceEntity {dataset:$dataset}) RETURN properties(n) AS props',dataset=dataset)]
        expected = [dict(row,dataset=dataset) for row in expected_entities]
        if sorted(actual,key=lambda r:r['id']) != sorted(expected,key=lambda r:r['id']):
            raise ValueError('Stored entity IDs/properties differ from inventory')
        # Include every relationship touching the namespace, including unexpected or cross-dataset links.
        actual_edges = [dict(r) for r in tx.run('MATCH (c)-[r]->(a) WHERE c.dataset=$dataset OR a.dataset=$dataset RETURN c.id AS circuit_id, a.id AS asset_id, c.dataset AS source_dataset, a.dataset AS target_dataset, type(r) AS rel_type, properties(r) AS props',dataset=dataset)]
        expected_edges = [dict(circuit_id=e['circuit_id'],asset_id=e['asset_id'],source_dataset=dataset,target_dataset=dataset,rel_type='REFERENCE_ENDPOINT',props={'position':e['position']}) for e in expected_endpoints]
        if sorted(map(canonical,actual_edges)) != sorted(map(canonical,expected_edges)):
            raise ValueError('Stored endpoint relationships differ from inventory')
        return dict(dataset=dataset, assets=len(payload['assets']), circuit_observations=len(payload['circuit_observations']),interface_assertions=len(payload.get('topology_interfaces',[])), endpoint_relationships=len(expected_endpoints),verified=True,mode='reference_only')
