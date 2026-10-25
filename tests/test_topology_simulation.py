import copy
import json
import unittest

from prism import create_app
from prism.simulation.topology import prepare_topology_scenario, topology_steps


class TopologySimulationTests(unittest.TestCase):
    def setUp(self):
        self.reference = dict(assets=[dict(id=a) for a in ['a', 'b', 'c', 'island']],
                              connections=[dict(id=i, source=a, target=b) for i, a, b in
                                           [('ab1', 'a', 'b'), ('ab2', 'a', 'b'), ('bc', 'b', 'c')]])

    def test_parallel_records_and_preexisting_islands_are_preserved(self):
        original = copy.deepcopy(self.reference)
        spec = prepare_topology_scenario(self.reference, dict(steps=4, faults=[
            dict(asset_id='ab1', step=1, duration_steps=1),
            dict(asset_id='bc', step=1, duration_steps=2)]))
        rows = list(topology_steps(self.reference, spec))
        self.assertEqual(rows[0]['component_count'], 2)
        self.assertEqual(rows[1]['component_count'], 3)
        self.assertEqual(rows[1]['newly_isolated_asset_ids'], ['c'])
        self.assertIn('ab2', rows[1]['active_connection_ids'])
        self.assertEqual(rows[3]['component_count'], 2)
        self.assertEqual(rows[3]['events'], [dict(asset_id='bc', event='restored')])
        self.assertEqual(self.reference, original)

    def test_node_outage_blocks_only_incident_records_and_restores(self):
        spec = prepare_topology_scenario(self.reference, dict(steps=3, faults=[
            dict(asset_id='b', step=1, duration_steps=1)]))
        rows = list(topology_steps(self.reference, spec))
        self.assertEqual(set(rows[1]['blocked_connection_ids']), {'ab1', 'ab2', 'bc'})
        self.assertNotIn('b', rows[1]['active_asset_ids'])
        self.assertEqual(rows[1]['newly_isolated_asset_ids'], ['a', 'c'])
        self.assertEqual(rows[2]['active_connection_ids'], ['ab1', 'ab2', 'bc'])

    def test_rejects_fixture_ids_bad_bounds_and_noninteger_values(self):
        invalid = [dict(steps=True), dict(steps=97), dict(interval_ms=0), dict(interval_ms=250.5),
                   dict(policy='q_learning'), dict(faults=[dict(asset_id='thermal_01', step=0, duration_steps=1)]),
                   dict(steps=2, faults=[dict(asset_id='a', step=2, duration_steps=1)])]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(ValueError):
                prepare_topology_scenario(self.reference, body)

    def test_stream_maps_exact_website_ids_and_computes_incrementally(self):
        sleeps = []
        app = create_app(dict(TESTING=True, TOPOLOGY_SIMULATION_SLEEP=sleeps.append))
        client = app.test_client()
        reference = client.get('/api/reference-grid').json
        identifier = reference['assets'][0]['id']
        response = client.post('/api/topology-scenario/stream', json=dict(
            steps=3, interval_ms=100, faults=[dict(asset_id=identifier, step=1, duration_steps=1)]), buffered=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        chunks = iter(response.response)
        start = json.loads(next(chunks))
        self.assertEqual(sleeps, [])
        self.assertEqual({a['id'] for a in start['assets']}, {a['id'] for a in reference['assets']})
        self.assertEqual({c['id'] for c in start['connections']}, {c['id'] for c in reference['connections']})
        rows = [json.loads(next(chunks)) for _ in range(3)]
        self.assertEqual(sleeps, [.1, .1, .1])
        self.assertEqual(rows[1]['failed_asset_ids'], [identifier])
        self.assertEqual(rows[2]['failed_asset_ids'], [])
        self.assertEqual(json.loads(next(chunks))['type'], 'complete')
        response.close()

    def test_concurrent_limit_and_disconnect_release_capacity(self):
        app = create_app(dict(TESTING=True, TOPOLOGY_SIMULATION_SLEEP=lambda _: None))
        client = app.test_client()
        first = client.post('/api/topology-scenario/stream', json={}, buffered=False)
        self.assertEqual(client.post('/api/topology-scenario/stream', json={}).status_code, 429)
        first.close()
        third = client.post('/api/topology-scenario/stream', json=dict(steps=1), buffered=False)
        self.assertEqual(third.status_code, 200)
        third.close()

    def test_missing_reference_is_not_replaced_with_teaching_grid(self):
        client = create_app(dict(TESTING=True, REFERENCE_DATASET_PATH='/missing/reference.json')).test_client()
        self.assertEqual(client.post('/api/topology-scenario/stream', json={}).status_code, 503)


if __name__ == '__main__':
    unittest.main()
