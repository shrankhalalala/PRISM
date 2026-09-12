"""Seed the optional local Neo4j service; credentials come from environment."""
import os
from prism.config import DATA_DIR
from prism.grid.model import load_grid
from prism.grid.neo4j_store import Neo4jStore

if __name__ == "__main__":
    password=os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("Export NEO4J_PASSWORD before seeding.")
    store=Neo4jStore(os.environ.get("NEO4J_URI","bolt://localhost:7687"),os.environ.get("NEO4J_USER","neo4j"),password)
    try:
        print(store.seed(load_grid(DATA_DIR / "raw/grid.json")))
    finally:
        store.close()
