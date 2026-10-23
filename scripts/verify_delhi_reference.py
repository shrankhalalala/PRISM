"""Live verification against a disposable Neo4j instance on port 17687."""

import json
import secrets
import subprocess
import time

from prism.grid.model import synthetic_grid
from prism.grid.neo4j_store import Neo4jStore
from prism.grid.reference import build_reference, canonical
from prism.grid.reference_store import Neo4jReferenceStore


def fixture_snapshot(store):
    with store.driver.session() as session:
        nodes=[dict(r['p']) for r in session.run('MATCH (n:PrismNode) RETURN properties(n) AS p')]
        edges=[dict(r) for r in session.run('MATCH (s:PrismNode)-[r:LINE]->(t:PrismNode) RETURN s.dataset AS dataset,s.id AS source,t.id AS target,properties(r) AS properties')]
    return sorted(map(canonical,nodes)),sorted(map(canonical,edges))


def main():
    name='prism-reference-check-'+secrets.token_hex(4)
    password=secrets.token_urlsafe(24)
    created=False
    reference=fixture=None
    try:
        subprocess.run(['docker','pull','neo4j:5.26-community'],check=True,timeout=300,stdout=subprocess.DEVNULL)
        subprocess.run(['docker','run','-d','--rm','--name',name,'-p','127.0.0.1:17687:7687','-e','NEO4J_AUTH=neo4j/'+password,'neo4j:5.26-community'],check=True,capture_output=True,timeout=30)
        created=True
        uri='bolt://127.0.0.1:17687'
        reference=Neo4jReferenceStore(uri,'neo4j',password)
        deadline=time.monotonic()+120
        while True:
            try:
                reference.driver.verify_connectivity(); break
            except Exception:
                if time.monotonic()>deadline: raise RuntimeError('Temporary Neo4j did not become ready') from None
                time.sleep(2)
        fixture=Neo4jStore(uri,'neo4j',password)
        fixture.seed(synthetic_grid(),'prism_phase1')
        fixture.seed(synthetic_grid(),'unrelated_fixture')
        before=fixture_snapshot(fixture)
        payload=build_reference()
        first=reference.seed(payload)
        second=reference.seed(payload)
        if first!=second or not second['verified']: raise AssertionError('Idempotency verification failed')
        if before!=fixture_snapshot(fixture): raise AssertionError('Existing fixtures changed')
        # Verify detection of incomplete/corrupted persisted graphs, not just counts.
        with reference.driver.session() as session:
            session.run('MATCH (n:PrismReferenceEntity {dataset:$dataset,id:$id}) SET n.record_json="corrupted"',dataset=payload['dataset'],id=payload['assets'][0]['id']).consume()
        try: reference.seed(payload)
        except ValueError: corruption_rejected=True
        else: raise AssertionError('Corrupted immutable dataset was accepted')
        print(json.dumps(dict(first_import=first,second_import=second,fixtures_unchanged=True,corruption_rejected=corruption_rejected,temporary_database_removed_on_exit=True),indent=2),flush=True)
    finally:
        if reference: reference.close()
        if fixture: fixture.close()
        if created: subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)


if __name__=='__main__': main()
