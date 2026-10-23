from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import unittest
from prism import create_app
from prism.data.stations import StationClient, parse_stations, REGISTRY

NOW=datetime(2026,10,23,tzinfo=timezone.utc)
def payload(value=-4):
    return {'data':[{'DG_GRID':'Pragati','DG_MW':value,'DG_MVAR':-2,'DG_VOLTAGE':220,'DG_DATE':NOW.isoformat(),'DG_STTS':1}]}

class StationTests(unittest.TestCase):
    def test_mapping_and_signed_values(self):
        p=json.loads(REGISTRY.read_text());ref=json.loads(Path('data/topology/delhi/reference_dataset.json').read_text())
        ids={a['id'] for a in ref['assets']}
        self.assertEqual(len(p['mappings']),49)
        self.assertTrue(all(v['asset_id'] in ids and v['evidence'] for v in p['mappings'].values()))
        self.assertEqual(len({v['asset_id'] for v in p['mappings'].values()}),49)
        self.assertEqual(parse_stations(payload(),NOW)['readings'][0]['mw'],-4)
        p=payload();p['data'].append({'DG_GRID':'new unknown station'})
        self.assertEqual(parse_stations(p,NOW)['unmatched_labels'],['new unknown station'])
        for v in [float('nan'),True,None]:
            with self.assertRaises(ValueError):parse_stations(payload(v),NOW)

    def test_cache_recovery_and_backward_time(self):
        timer=[0];now=[NOW];calls=[];raw=[payload()]
        def fetch():calls.append(1);return raw[0]
        c=StationClient(fetch,lambda:now[0],lambda:timer[0])
        self.assertEqual(c.snapshot()['status'],'live');c.snapshot();self.assertEqual(len(calls),1)
        timer[0]=61;raw[0]=payload();raw[0]['data'][0]['DG_DATE']=(NOW-timedelta(minutes=1)).isoformat()
        self.assertEqual(c.snapshot()['status'],'stale')
        timer[0]=122;raw[0]=payload();self.assertEqual(c.snapshot()['status'],'live')
        now[0]+=timedelta(minutes=6);self.assertEqual(c.snapshot()['status'],'stale')

    def test_api_unavailable_and_no_generation_inference(self):
        client=create_app({'TESTING':True,'STATION_CLIENT':StationClient(lambda:payload(),lambda:NOW)}).test_client()
        body=client.get('/api/live/stations').get_json()
        self.assertEqual(body['coverage']['measured_assets'],1)
        self.assertEqual(len(body['coverage']['unavailable_asset_ids']),65)
        self.assertEqual(client.get('/api/live/assets/ss-pragati').get_json()['reading']['measurement_role'],'station_loading')
        self.assertIsNone(client.get('/api/live/assets/plant-pps1').get_json()['reading'])
        self.assertEqual(client.get('/api/live/assets/nope').status_code,404)
        bad=create_app({'TESTING':True,'STATION_CLIENT':StationClient(lambda:{})}).test_client()
        self.assertEqual(bad.get('/api/live/stations').status_code,503)
