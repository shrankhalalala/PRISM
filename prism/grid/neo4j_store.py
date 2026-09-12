"""Optional idempotent Neo4j persistence, scoped to a named dataset."""
from prism.grid.model import validate_grid


class Neo4jStore:
    """Store all node/line properties without changing other datasets."""
    def __init__(self, uri: str, user: str, password: str):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user,password))

    def close(self):
        """Release driver connections."""
        self.driver.close()

    def seed(self, grid: dict, dataset: str = "prism_phase1") -> dict:
        """Atomically replace this dataset only; unique keys support repeated seeds."""
        validate_grid(grid)
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT prism_node_key IF NOT EXISTS FOR (n:PrismNode) REQUIRE (n.dataset, n.id) IS UNIQUE").consume()
            session.execute_write(self._write,grid,dataset)
            record=session.run("MATCH (n:PrismNode {dataset:$dataset}) OPTIONAL MATCH (n)-[r:LINE]->() RETURN count(DISTINCT n) AS nodes, count(r) AS edges",dataset=dataset).single()
            return dict(record)

    @staticmethod
    def _write(tx,grid,dataset):
        """Replace a namespaced fixture in one transaction."""
        tx.run("MATCH (n:PrismNode {dataset:$dataset}) DETACH DELETE n",dataset=dataset).consume()
        tx.run("UNWIND $nodes AS row CREATE (n:PrismNode) SET n = row, n.dataset = $dataset",nodes=grid["nodes"],dataset=dataset).consume()
        tx.run("UNWIND $edges AS row MATCH (s:PrismNode {dataset:$dataset,id:row.source}), (t:PrismNode {dataset:$dataset,id:row.target}) CREATE (s)-[r:LINE]->(t) SET r = row",edges=grid["edges"],dataset=dataset).consume()
