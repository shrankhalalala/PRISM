"""Reference-view completeness, provenance and fixture isolation."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from prism import create_app
from prism.config import ROOT


class ReferenceAPITests(unittest.TestCase):
    def setUp(self):
        self.client=create_app({'TESTING':True}).test_client()

    def test_every_reference_record_is_accessible_without_changing_synthetic_grid(self):
        original=json.loads((ROOT/'data/topology/delhi/reference_dataset.json').read_text())
        response=self.client.get('/api/reference-grid')
        self.assertEqual(response.status_code,200)
        view=response.get_json()
        self.assertEqual({a['id'] for a in view['assets']},{a['id'] for a in original['assets']})
        expected={c['id'] for c in original['circuit_observations']+original['topology_interfaces']}
        self.assertEqual({c['id'] for c in view['connections']},expected)
        self.assertEqual(len(view['assets']),66)
        self.assertEqual(len(view['connections']),261)
        for asset in view['assets']:
            self.assertIsNone(asset['current_output_mw'])
            self.assertTrue(0<=asset['layout']['x']<=1000)
            self.assertTrue(0<=asset['layout']['y']<=700)
        for connection in view['connections']:
            self.assertTrue(all(e in view['evidence'] for e in connection['evidence_ids']))
        synthetic=self.client.get('/api/grid').get_json()
        self.assertEqual(synthetic['data_source'],'synthetic')
        self.assertEqual(len(synthetic['nodes']),12)
        self.assertEqual(len(synthetic['edges']),12)

    def test_detail_source_links_unknown_values_and_cache_contract(self):
        asset=self.client.get('/api/reference-grid/assets/ss-dwarka-sector-5').get_json()
        self.assertEqual(asset['mode'],'reference_only')
        self.assertIsNone(asset['asset']['latitude'])
        self.assertTrue(asset['connections'])
        self.assertTrue(all(e['url'].startswith('https://') for e in asset['evidence'].values()))
        self.assertEqual(self.client.get('/api/reference-grid/assets/missing').status_code,404)
        response=self.client.get('/api/reference-grid')
        cached=self.client.get('/api/reference-grid',headers={'If-None-Match':response.headers['ETag']})
        self.assertEqual(cached.status_code,304)

    def test_missing_or_corrupt_reference_is_not_replaced_with_synthetic_data(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'reference.json'
            client=create_app({'TESTING':True,'REFERENCE_DATASET_PATH':path}).test_client()
            self.assertEqual(client.get('/api/reference-grid').status_code,503)
            path.write_text('{"mode":"reference_only"}')
            self.assertEqual(client.get('/api/reference-grid').status_code,503)
            self.assertEqual(client.get('/api/reference-grid/assets/ss-pragati').status_code,503)
            self.assertEqual(client.get('/api/grid').status_code,200)


if __name__=='__main__': unittest.main()
