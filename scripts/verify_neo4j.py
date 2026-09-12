"""Opt-in integration check with an isolated temporary Docker container.

Runs an idempotent seed check on port 17687, then removes only its own container.
Requires Docker, network access for the image, and the optional neo4j dependency.
"""
import secrets
import subprocess
import time
from prism.grid.model import synthetic_grid
from prism.grid.neo4j_store import Neo4jStore


def main():
    """Create a disposable database, seed twice, verify counts, and clean up."""
    name="prism-phase1-check-"+secrets.token_hex(4)
    password=secrets.token_urlsafe(24)
    created=False
    store=None
    try:
        subprocess.run(['docker','pull','neo4j:5.26-community'],check=True,timeout=240)
        subprocess.run(['docker','run','-d','--rm','--name',name,'-p','127.0.0.1:17687:7687','-e','NEO4J_AUTH=neo4j/'+password,'neo4j:5.26-community'],check=True,capture_output=True,timeout=30)
        created=True
        store=Neo4jStore('bolt://127.0.0.1:17687','neo4j',password)
        deadline=time.monotonic()+90
        while True:
            try:
                store.driver.verify_connectivity()
                break
            except Exception:
                if time.monotonic()>=deadline:
                    raise RuntimeError('Temporary Neo4j did not become ready') from None
                time.sleep(2)
        for run in [1,2]:
            counts=store.seed(synthetic_grid())
            if counts != {'nodes':12,'edges':12}:
                raise AssertionError(counts)
            print(f'Seed {run}: 12 nodes, 12 edges',flush=True)
        print('PASS: live Neo4j import and idempotency verified.',flush=True)
    finally:
        if store:
            store.close()
        if created:
            subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)

if __name__=='__main__':
    main()
