"""Acceptance tests for the completed Phase 2 model and scenario artifacts."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import pandas as pd

from prism.config import DATA_DIR, ROOT
from prism.dispatch.evaluation import baseline_action, load_scenario_suite, make_environment, run_policy
from prism.forecasting import LSTMConfig, LSTMForecaster
from prism.grid.model import load_grid


class LSTMTests(unittest.TestCase):
    def test_fit_predict_and_artifact_round_trip(self):
        values=50+10*np.sin(np.arange(80)*np.pi/12)
        frame=pd.DataFrame({'demand_mw':values})
        model=LSTMForecaster(LSTMConfig(window=8,hidden_size=4,epochs=2,max_windows_per_epoch=24,seed=5)).fit(frame,'demand_mw')
        prediction=model.predict(frame,3)
        self.assertEqual(len(prediction),3)
        self.assertTrue(all(np.isfinite(prediction)))
        with TemporaryDirectory() as directory:
            path=Path(directory)/'model.json'
            model.save(path)
            loaded=LSTMForecaster.load(path)
            np.testing.assert_allclose(prediction,loaded.predict(frame,3))

    def test_committed_models_match_all_targets(self):
        for target in ('demand_mw','solar_mw','wind_mw'):
            model=LSTMForecaster.load(ROOT/'models/forecasting'/f'{target}_lstm.json')
            self.assertEqual(model.target,target)


class ScenarioEvidenceTests(unittest.TestCase):
    def test_suite_contains_partitioned_phase2_scenarios(self):
        suite=load_scenario_suite(DATA_DIR/'scenarios/phase2_scenarios.json')
        partitions={item['partition'] for item in suite['scenarios']}
        self.assertEqual(partitions,{'train','validation','test'})

    def test_held_out_scenario_is_reproducible(self):
        suite=load_scenario_suite(DATA_DIR/'scenarios/phase2_scenarios.json')
        scenario=next(item for item in suite['scenarios'] if item['id']=='line_fault')
        frame=pd.read_csv(DATA_DIR/'processed/measurements.csv')
        topology=load_grid(DATA_DIR/'raw/grid.json')
        first=run_policy(make_environment(topology,frame,scenario,42),baseline_action,42)
        second=run_policy(make_environment(topology,frame,scenario,42),baseline_action,42)
        self.assertEqual(first,second)
        self.assertEqual(first['steps'],96)

    def test_committed_reports_record_negative_results_too(self):
        dispatch=json.loads((ROOT/'reports/phase2_dispatch.json').read_text())
        forecast=json.loads((ROOT/'reports/phase2_forecasting.json').read_text())
        self.assertEqual(len(dispatch['per_seed']),5)
        self.assertEqual(forecast['split']['method'],'chronological_70_15_15')
        self.assertIn('standard_deviation_across_training_seeds',dispatch['paired_test_summary']['q_learning_return'])


if __name__=='__main__':
    unittest.main()
