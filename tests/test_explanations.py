from datetime import datetime,timezone
import unittest
from prism import create_app
from prism.explain.diagnosis import diagnose,fixed_pagerank
from prism.simulation import Observation,Action
import networkx as nx

class ExplanationTests(unittest.TestCase):
    def test_actual_attribution_additivity_and_scope(self):
        try:from prism.explain.attribution import explain;r=explain(Observation(500,400,100),tuple(Action))
        except (ImportError,OSError):self.skipTest('Phase3 extras/artifacts required')
        self.assertLess(abs(r['additivity_residual']),1e-4)
        self.assertEqual(r['background_samples'],100);self.assertEqual(r['explained_action'],r['surrogate_action'])
        self.assertEqual(len(r['factors']),10);self.assertFalse(r['executable'])

    def test_diagnosis_paths_and_unknowns(self):
        stamp=datetime.now(timezone.utc).isoformat()
        r=diagnose({'dataset':'synthetic','alarms':[{'asset_id':'gas','observed_at':stamp}]})
        self.assertFalse(r['verified_cause']);self.assertEqual(r['iterations'],10)
        self.assertEqual(r['hypotheses'][0]['asset_id'],'gas')
        with self.assertRaises(ValueError):diagnose({'dataset':'synthetic','alarms':[{'asset_id':'unknown','observed_at':stamp}]})
        with self.assertRaises(ValueError):diagnose({'alarms':[{'asset_id':'ss-pragati','observed_at':'2026-01-01'}]})
        rank,_=fixed_pagerank(nx.path_graph(5));self.assertAlmostEqual(sum(rank.values()),1)

    def test_api_validation(self):
        c=create_app({'TESTING':True}).test_client()
        self.assertEqual(c.post('/api/explain',json={}).status_code,400)
        self.assertEqual(c.post('/api/diagnose',json={'dataset':'bad','alarms':[]}).status_code,400)
