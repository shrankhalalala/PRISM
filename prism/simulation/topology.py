"""Paced, read-only connectivity scenarios on the website's reference identities.

This models removal/restoration of dated reference records, not electrical flow,
energization, protection, dispatch, or actual Delhi outages.
"""
from datetime import datetime, timezone
import json
from threading import BoundedSemaphore
import time

import networkx as nx
from flask import Blueprint, Response, current_app, jsonify, request

from prism.config import ROOT
from prism.grid.presentation import reference_view

api = Blueprint('topology_simulation', __name__)
ASSURANCE = ('Reference-connectivity simulation using dated circuits and interface '
             'assertions. Outages are hypothetical; no power flow, electrical '
             'limits, live switching state or station MW effects are calculated.')


def integer(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
        raise ValueError(f'{name} must be an integer between {lower} and {upper}')
    return value


def prepare_topology_scenario(reference, body):
    if not isinstance(body, dict) or set(body) - {'steps', 'interval_ms', 'faults'}:
        raise ValueError('Provide steps, interval_ms and faults only')
    steps = integer(body.get('steps', 24), 'steps', 1, 96)
    interval = integer(body.get('interval_ms', 250), 'interval_ms', 100, 1000)
    faults = body.get('faults', [])
    if not isinstance(faults, list) or len(faults) > 8:
        raise ValueError('faults must be an array of at most eight outages')
    known = {a['id'] for a in reference['assets']} | {c['id'] for c in reference['connections']}
    checked = []
    for fault in faults:
        if not isinstance(fault, dict) or set(fault) != {'asset_id', 'step', 'duration_steps'}:
            raise ValueError('Each outage needs asset_id, step and duration_steps')
        identifier = fault['asset_id']
        if not isinstance(identifier, str) or identifier not in known:
            raise ValueError('Outage target must be an existing Delhi asset or connection ID')
        checked.append(dict(asset_id=identifier,
                            step=integer(fault['step'], 'fault step', 0, steps - 1),
                            duration_steps=integer(fault['duration_steps'], 'duration_steps', 1, 96)))
    return dict(steps=steps, interval_ms=interval, faults=checked)


def topology_steps(reference, specification):
    """Yield newly computed states; never mutate the shared reference export."""
    assets = {a['id'] for a in reference['assets']}
    records = reference['connections']
    baseline = nx.Graph()
    baseline.add_nodes_from(assets)
    baseline.add_edges_from((c['source'], c['target']) for c in records)
    baseline_linked = {a for a in assets if baseline.degree(a) > 0}
    previous = set()
    for index in range(specification['steps']):
        failed = {f['asset_id'] for f in specification['faults']
                  if f['step'] <= index < f['step'] + f['duration_steps']}
        failed_assets = failed & assets
        failed_connections = failed - assets
        blocked = {c['id'] for c in records if c['id'] in failed_connections
                   or c['source'] in failed_assets or c['target'] in failed_assets}
        graph = nx.Graph()
        graph.add_nodes_from(assets - failed_assets)
        graph.add_edges_from((c['source'], c['target']) for c in records if c['id'] not in blocked)
        components = sorted((sorted(group) for group in nx.connected_components(graph)),
                            key=lambda group: (-len(group), group))
        isolated = sorted(nx.isolates(graph))
        yield dict(type='step', step=index, total_steps=specification['steps'],
                   simulated_minutes=index * 15,
                   emitted_at=datetime.now(timezone.utc).isoformat(),
                   failed_asset_ids=sorted(failed_assets),
                   failed_connection_ids=sorted(failed_connections),
                   blocked_connection_ids=sorted(blocked),
                   active_asset_ids=sorted(graph.nodes),
                   active_connection_ids=[c['id'] for c in records if c['id'] not in blocked],
                   components=components, component_count=len(components),
                   isolated_asset_ids=isolated,
                   newly_isolated_asset_ids=sorted(set(isolated) & baseline_linked),
                   events=([dict(asset_id=a, event='outage') for a in sorted(failed - previous)] +
                           [dict(asset_id=a, event='restored') for a in sorted(previous - failed)]))
        previous = failed


@api.record_once
def configure(state):
    # Leave a thread available for readings/health on the two-thread web workers.
    state.app.extensions['topology_simulation_slots'] = BoundedSemaphore(1)


@api.post('/api/topology-scenario/stream')
def stream():
    if not request.is_json:
        return jsonify(error='invalid_request', message='Use application/json'), 415
    try:
        reference = reference_view(current_app.config.get(
            'REFERENCE_DATASET_PATH', ROOT / 'data/topology/delhi/reference_dataset.json'))
    except (OSError, ValueError, TypeError, KeyError):
        return jsonify(error='reference_data_unavailable'), 503
    try:
        specification = prepare_topology_scenario(reference, request.get_json())
    except (ValueError, TypeError) as exc:
        return jsonify(error='invalid_request', message=str(exc)), 400
    slots = current_app.extensions['topology_simulation_slots']
    if not slots.acquire(blocking=False):
        return jsonify(error='simulation_busy', message='A topology stream is active on this worker; retry shortly.'), 429
    sleep = current_app.config.get('TOPOLOGY_SIMULATION_SLEEP', time.sleep)

    def encode(value):
        return json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n'

    def generate():
        try:
            baseline = next(topology_steps(reference, dict(steps=1, faults=[])))
            yield encode(dict(type='start', model='reference_connectivity', data_source='delhi_reference',
                              dataset=reference['dataset'], assurance=ASSURANCE,
                              step_minutes=15, **specification,
                              assets=[{k: a[k] for k in ('id', 'name', 'kind', 'layout')} for a in reference['assets']],
                              connections=[{k: c[k] for k in ('id', 'source', 'target', 'assertion_only')}
                                           for c in reference['connections']], baseline=baseline))
            snapshots = topology_steps(reference, specification)
            for _ in range(specification['steps']):
                sleep(specification['interval_ms'] / 1000)
                yield encode(next(snapshots))
            yield encode(dict(type='complete', status='completed', steps=specification['steps']))
        except GeneratorExit:
            raise
        except Exception:
            yield encode(dict(type='error', message='Topology run interrupted. Start a new run to retry.'))
        finally:
            release()

    released = False

    def release():
        nonlocal released
        if not released:
            released = True
            slots.release()

    response = Response(generate(), mimetype='application/x-ndjson',
                        headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
    response.call_on_close(release)
    return response
