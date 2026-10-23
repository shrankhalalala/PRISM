import unittest
from prism import create_app
from prism.simulation.runner import run_scenario,ScenarioCancelled

class OperationsTests(unittest.TestCase):
    def test_shared_runner_cancel_and_bounds(self):
        with self.assertRaises(ScenarioCancelled):run_scenario({'steps':96},checkpoint=lambda *_:False)
        for value in [True,0,97,'8']:
            with self.assertRaises(ValueError):run_scenario({'steps':value})
        result=run_scenario({'steps':2,'seed':42})
        self.assertEqual(result['steps'],2);self.assertEqual(result['data_source'],'synthetic')
        self.assertIn('totals',result)

    def test_mutations_require_configured_token(self):
        c=create_app({'TESTING':True,'OPERATOR_TOKEN':'test-only'}).test_client()
        for url in ['/api/jobs','/api/advisories','/api/jobs/00000000-0000-0000-0000-000000000000/cancel']:
            self.assertEqual(c.post(url,json={}).status_code,401)
        self.assertEqual(c.get('/api/jobs/not-a-uuid').status_code,400)
        self.assertEqual(c.post('/api/jobs',json={},headers={'X-PRISM-Operator-Token':'test-only'}).status_code,400)

    def test_data_quality_alerts_not_inferred_grid_faults(self):
        class Source:
            def snapshot(self):return {'status':'unavailable'}
        c=create_app({'TESTING':True,'GRIDWATCH_CLIENT':Source(),'STATION_CLIENT':Source()}).test_client()
        result=c.get('/api/alerts').json
        self.assertTrue(result['advisory_only']);self.assertTrue(any(a['category']=='data_quality' for a in result['alerts']))
        self.assertFalse(any(a['category']=='grid_fault' for a in result['alerts']))
