"""Initialize durable schemas and import the validated reference without resetting volumes."""
from prism.operations.store import initialize
from prism.streaming.store import connections,DurableStream
from prism.forecasting.registry import bootstrap
from prism.grid.reference import build_reference
from prism.grid.reference_store import Neo4jReferenceStore
import os


def main():
    initialize();r,db=connections()
    try:DurableStream(r,db).setup()
    finally:db.close();r.close()
    bootstrap()
    store=Neo4jReferenceStore(os.environ['NEO4J_URI'],os.environ.get('NEO4J_USER','neo4j'),os.environ['NEO4J_PASSWORD'])
    try:store.seed(build_reference())
    finally:store.close()
    print('Phase 3 initialization complete; existing datasets preserved.')

if __name__=='__main__':main()
