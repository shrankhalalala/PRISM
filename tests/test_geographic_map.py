"""Geographic display data must not silently promote unresolved reference identities."""
import json
from pathlib import Path
import unittest
from prism import create_app
from prism.config import ROOT


class GeographicMapTests(unittest.TestCase):
    def setUp(self):
        self.document=json.loads((ROOT/'prism/static/delhi-asset-locations.json').read_text())
        self.reference=json.loads((ROOT/'data/topology/delhi/reference_dataset.json').read_text())

    def test_location_points_have_known_asset_ids_and_traceable_sources(self):
        identifiers={a['id'] for a in self.reference['assets']}
        self.assertTrue(self.document['locations'])
        for identifier,point in self.document['locations'].items():
            self.assertIn(identifier,identifiers)
            self.assertTrue(26 < point['latitude'] < 31)
            self.assertTrue(74 < point['longitude'] < 80)
            source=self.document['sources'][point['source_id']]
            self.assertTrue(source['url'].startswith('https://'))
            self.assertTrue(source['license'])
            self.assertTrue(point['source_record'])

    def test_ambiguous_place_names_are_not_assigned_town_centres(self):
        for identifier in ['ss-noida','ss-noida-62','plant-jhajjar']:
            self.assertNotIn(identifier,self.document['locations'])
        self.assertTrue(all(a['latitude'] is None and a['longitude'] is None for a in self.reference['assets']))

    def test_map_assets_are_served_and_reference_contract_is_preserved(self):
        client=create_app({'TESTING':True}).test_client()
        for filename in ['leaflet.js','leaflet.css','delhi-asset-locations.json']:
            with client.get('/static/'+filename) as response:
                self.assertEqual(response.status_code,200)
        payload=client.get('/api/reference-grid').get_json()
        self.assertEqual(payload['dataset'],self.reference['dataset'])
        self.assertEqual(len(payload['assets']),len(self.reference['assets']))
        self.assertTrue(all(a['latitude'] is None for a in payload['assets']))


if __name__=='__main__':unittest.main()
