"""Regression checks for evidence isolation and candidate model compatibility."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from prism.grid.reference import build_reference
from prism.grid.eligibility import voltage_evidence_graph, electrical_readiness
from prism.forecasting.direct import DirectDayAheadForecaster,load_autoregressive
from prism.forecasting import LSTMForecaster,LSTMConfig
from prism.dispatch.refinement import StateAwareQLearningAgent,richer_state
from prism.dispatch.q_learning import TrainingConfig
from prism.dispatch.evaluation import baseline_action
from prism.simulation import Observation,Action


class RefinementTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame(dict(timestamp=pd.date_range('2025-01-01',periods=120,freq='h',tz='UTC'),demand_mw=500+50*np.sin(np.arange(120)*2*np.pi/24)))

    def test_source_voltage_layers_do_not_infer_transformers(self):
        reference=build_reference();before=json.dumps(reference,sort_keys=True)
        graph=voltage_evidence_graph(reference,'later_dtl_table')
        self.assertEqual(graph.number_of_edges(),129)
        self.assertTrue(all(a[1]==b[1] for a,b in graph.edges()))
        self.assertTrue(all(d['temporal_class']=='later_dtl_table' for _,_,d in graph.edges(data=True)))
        self.assertFalse(electrical_readiness(reference)['dispatch_training_eligible'])
        self.assertEqual(before,json.dumps(reference,sort_keys=True))
        with self.assertRaises(ValueError):voltage_evidence_graph(reference,'current')

    def test_direct_roundtrip_and_gaps(self):
        frame=self.frame();model=DirectDayAheadForecaster().fit(frame)
        expected=model.predict(frame.tail(24))
        self.assertEqual(len(expected),24)
        self.assertTrue(np.isfinite(expected).all())
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ar.json';model.save(path,{'hourly_sha256':'test'})
            np.testing.assert_allclose(load_autoregressive(path).predict(frame.tail(24)),expected)
            payload=json.loads(path.read_text());payload['coefficients'][0][0]=float('nan');path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):load_autoregressive(path)
        with self.assertRaises(ValueError):model.predict(frame.drop(index=110).tail(24))
        broken=frame.iloc[::2].reset_index(drop=True)
        with self.assertRaises(ValueError):DirectDayAheadForecaster().fit(broken)

    def test_seasonal_lstm_roundtrip_and_default_compatibility(self):
        frame=self.frame()
        model=LSTMForecaster(LSTMConfig(epochs=1,max_windows_per_epoch=3,seasonal_residual=True)).fit(frame,'demand_mw')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'lstm.json';model.save(path)
            np.testing.assert_allclose(model.predict(frame,24),LSTMForecaster.load(path).predict(frame,24))
        self.assertFalse(LSTMConfig().seasonal_residual)
        with self.assertRaises(ValueError):LSTMConfig(window=12,seasonal_residual=True)

    def test_sparse_dispatch_fallback_mask_and_terminal_update(self):
        agent=StateAwareQLearningAgent(TrainingConfig(episodes=1))
        observation=Observation(500,450,100)
        valid=(Action.HOLD,Action.INCREASE_GENERATION)
        self.assertEqual(agent.action(observation,valid),baseline_action(observation,valid))
        self.assertNotEqual(richer_state(observation,valid),richer_state(observation,(Action.HOLD,)))
        agent.current_valid=valid;row=agent.row(observation,valid);old=row[0]
        agent._update(observation,Action.HOLD,2.,observation,(),True)
        self.assertAlmostEqual(row[0],old+.1*(2-old))
        self.assertEqual(agent.action(observation,(Action.HOLD,)),Action.HOLD)
