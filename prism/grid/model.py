"""Synthetic topology creation and validation; not an electrical flow solver."""
import json
import math
from pathlib import Path
import networkx as nx


def synthetic_grid() -> dict:
    """Build a fictional 12-node Delhi-inspired teaching network, in MW."""
    nodes = [
        dict(id="coal", name="Thermal One", kind="plant", fuel="coal", capacity_mw=600, output_mw=400, x=100, y=90),
        dict(id="gas", name="Gas Reserve", kind="plant", fuel="gas", capacity_mw=250, output_mw=100, x=310, y=90),
        dict(id="solar", name="Solar Park", kind="plant", fuel="solar", capacity_mw=200, output_mw=120, x=520, y=90),
        dict(id="wind", name="Wind Import", kind="plant", fuel="wind", capacity_mw=150, output_mw=80, x=730, y=90),
    ]
    for i, name in enumerate(["North", "East", "Central", "South"]):
        nodes.append(dict(id=f"sub_{i}", name=f"{name} Hub", kind="substation", voltage_kv=220, x=100+i*210, y=250))
        nodes.append(dict(id=f"load_{i}", name=f"{name} District", kind="load", demand_mw=[160,180,200,160][i], priority="critical" if i==2 else "normal", x=100+i*210, y=410))
    for node in nodes:
        node["status"] = "online"
    pairs = [(p, f"sub_{i}", 650) for i,p in enumerate(["coal","gas","solar","wind"])]
    pairs += [(f"sub_{i}", f"sub_{i+1}", 400) for i in range(3)] + [("sub_3","sub_0",400)]
    pairs += [(f"sub_{i}",f"load_{i}",300) for i in range(4)]
    edges = [dict(id=f"line_{i+1:02}", source=s, target=t, capacity_mw=c, status="online") for i,(s,t,c) in enumerate(pairs)]
    return dict(schema_version="1.0", data_source="synthetic", description="Fictional teaching network; not verified Delhi topology.", nodes=nodes, edges=edges)


def validate_grid(payload: dict) -> nx.Graph:
    """Check unique identifiers, finite ratings, endpoints, and connectivity."""
    graph = nx.Graph()
    nodes = payload.get("nodes", [])
    if not nodes:
        raise ValueError("Grid must contain nodes")
    for node in nodes:
        identifier = node.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in graph:
            raise ValueError("Node IDs must be nonempty and unique")
        if node.get("kind") not in {"plant", "substation", "load"}:
            raise ValueError("Invalid node kind")
        if node.get("status") not in {"online", "offline"}:
            raise ValueError("Invalid node status")
        required = {"plant": ["capacity_mw", "output_mw"], "load": ["demand_mw"], "substation": ["voltage_kv"]}[node["kind"]]
        for key in required:
            value = node.get(key)
            if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid {key} for {identifier}")
        if node["kind"] == "plant" and node["output_mw"] > node["capacity_mw"]:
            raise ValueError("Plant output exceeds capacity")
        graph.add_node(identifier, **node)
    edge_ids = set()
    for edge in payload.get("edges", []):
        s,t = edge.get("source"), edge.get("target")
        if s not in graph or t not in graph or s == t:
            raise ValueError("Invalid line endpoints")
        if not edge.get("id") or edge["id"] in edge_ids or graph.has_edge(s,t):
            raise ValueError("Duplicate line ID or endpoints")
        c = edge.get("capacity_mw")
        if isinstance(c,bool) or not isinstance(c,(int,float)) or not math.isfinite(c) or c <= 0:
            raise ValueError("Line capacity must be positive and finite")
        if edge.get("status") not in {"online", "offline"}:
            raise ValueError("Invalid line status")
        edge_ids.add(edge["id"])
        graph.add_edge(s,t, **edge)
    if not nx.is_connected(graph):
        raise ValueError("Initial topology must be connected")
    return graph


def grid_summary(payload: dict) -> dict:
    """Return aggregate power, explicitly without allocating line flows."""
    generation = sum(n.get("output_mw",0) for n in payload["nodes"] if n["status"] == "online")
    demand = sum(n.get("demand_mw",0) for n in payload["nodes"])
    return dict(nodes=len(payload["nodes"]), edges=len(payload["edges"]), generation_mw=generation, demand_mw=demand, balance_mw=generation-demand)


def load_grid(path: Path) -> dict:
    """Read and validate topology from JSON."""
    payload = json.loads(path.read_text())
    validate_grid(payload)
    return payload
