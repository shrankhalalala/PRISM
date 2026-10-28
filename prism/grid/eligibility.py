"""Voltage-layer evidence views; never infer buses, switches or electrical limits."""
from collections import Counter
import networkx as nx
from prism.grid.reference import validate_reference


def voltage_evidence_graph(reference, temporal_class):
    """Keep site/voltage endpoints and parallel records within one source cohort.

    These endpoints are voltage layers, not verified physical buses. No implicit
    transformer edge joins a site's 220 and 400 kV layers.
    """
    validate_reference(reference)
    available = {row['temporal_class'] for row in reference['circuit_observations']}
    if temporal_class not in available:
        raise ValueError('Unknown source cohort')
    graph = nx.MultiGraph(temporal_class=temporal_class, electrical_simulation_ready=False)
    for row in reference['circuit_observations']:
        if row['temporal_class'] != temporal_class:
            continue
        endpoints = [(asset_id, row['voltage_kv']) for asset_id in row['endpoint_node_ids']]
        for asset_id, voltage in endpoints:
            graph.add_node((asset_id, voltage), asset_id=asset_id, voltage_kv=voltage, physical_bus_verified=False)
        graph.add_edge(*endpoints, key=row['id'], **row)
    return graph


def electrical_readiness(reference):
    """Produce per-record acquisition requirements from the reviewed inventory."""
    validate_reference(reference)
    circuits = []
    for row in reference['circuit_observations']:
        missing = [field for field in ('thermal_limit_mw', 'resistance_ohm', 'reactance_ohm') if row.get(field) is None]
        missing.extend(['verified_terminal_bus_ids', 'dated_switching_state'])
        circuits.append(dict(id=row['id'], source_id=row['source_id'], voltage_kv=row['voltage_kv'], endpoint_asset_ids=row['endpoint_node_ids'], missing=missing, open_issue_ids=row.get('open_issue_ids', [])))
    cohorts = {}
    for cohort in sorted({r['temporal_class'] for r in reference['circuit_observations']}):
        graph = voltage_evidence_graph(reference, cohort)
        cohorts[cohort] = dict(voltage_layer_endpoints=len(graph), records=graph.number_of_edges(), evidence_components=nx.number_connected_components(graph), source_ids=sorted({r['source_id'] for r in reference['circuit_observations'] if r['temporal_class']==cohort}))
    return dict(reference_sha256=reference['content_sha256'], electrical_simulation_ready=False, dispatch_training_eligible=False,
                cohorts=cohorts, circuit_requirements=circuits,
                missing_field_counts=dict(Counter(field for row in circuits for field in row['missing'])),
                field_questions=reference['topology_coverage']['field_questions'],
                interface_assertions_excluded=len(reference['topology_interfaces']),
                limitation='Source cohorts are not current operating snapshots. Voltage layers are not verified buses; component counts describe evidence only. No transformer, capacity, impedance or switch inferred.')
