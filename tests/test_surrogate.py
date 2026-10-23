import unittest
from prism import create_app
from prism.dispatch.surrogate import FEATURES,features
from prism.dispatch.q_learning import ACTION_ORDER
from prism.simulation import Observation,Action

class SurrogateTests(unittest.TestCase):
    def test_feature_semantics_and_mask(self):
        row=features(Observation(100,80,20,.5,-.2,True),(Action.HOLD,Action.SHED))
        self.assertEqual(len(row),10);self.assertEqual(len(FEATURES),10)
        self.assertEqual(row[-1],33);self.assertEqual(row[6],20)
        with self.assertRaises(ValueError):features(Observation(100,80,20),())
        with self.assertRaises(ValueError):features(Observation(100,80,20),(Action.HOLD,Action.HOLD))

    def test_actual_model_schema_probabilities_and_masks(self):
        try:from prism.dispatch.api import get_surrogate;model=get_surrogate()
        except (ImportError,OSError):self.skipTest('Install phase3 extras and train surrogate')
        result=model.predict(Observation(500,400,100),(Action.HOLD,))
        self.assertEqual(result['surrogate_action'],'hold');self.assertEqual(result['q_action'],'hold')
        self.assertAlmostEqual(sum(result['probabilities'].values()),1,places=5)
        self.assertEqual(set(result['probabilities']),{a.value for a in ACTION_ORDER})
        self.assertFalse(result['executable'])

    def test_api_rejects_bad_context(self):
        c=create_app({'TESTING':True}).test_client()
        self.assertEqual(c.post('/api/dispatch/surrogate',json={}).status_code,400)
        self.assertEqual(c.post('/api/dispatch/surrogate',json={'observation':{'demand_mw':100,'generation_mw':90,'reserve_mw':5},'valid_actions':[]}).status_code,400)
