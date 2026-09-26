"""Behavioral acceptance checks for Phase 1; run with unittest discover."""
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import pandas as pd
from prism import create_app
from prism.config import DATA_DIR
from prism.data.pipeline import clean_measurements
from prism.grid.model import synthetic_grid, validate_grid, grid_summary
from prism.simulation.environment import GridEnvironment, Observation, Action
from prism.dispatch.baseline import recommend, encode_state


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.data=pd.read_csv(DATA_DIR / "raw/synthetic_measurements.csv").head(4)

    def test_sort_and_preserve_source(self):
        clean,report=clean_measurements(self.data.iloc[::-1])
        self.assertTrue(clean.timestamp.is_monotonic_increasing)
        self.assertEqual(report['accepted_rows'],4)
        self.assertTrue((clean.source=='synthetic_seed_42').all())

    def test_bad_values_rejected_and_gap_reported(self):
        self.data.loc[1,'demand_mw']=-1
        self.data.loc[2,'solar_mw']=float('inf')
        clean,report=clean_measurements(self.data)
        self.assertEqual(len(clean),2)
        self.assertEqual(report['rejected_rows'],2)
        self.assertEqual(report['gaps'][0]['missing_hours'],2)
        self.assertEqual(report['imputed_rows'],0)

    def test_duplicate_conflicts_all_rejected(self):
        duplicate=self.data.iloc[[0]].copy()
        duplicate['demand_mw']=999
        clean,report=clean_measurements(pd.concat([self.data,duplicate]))
        self.assertEqual(len(clean),3)
        self.assertEqual(report['reasons']['duplicate_timestamp'],2)

    def test_naive_and_off_grid_times_rejected(self):
        self.data.loc[0,'timestamp']='2026-01-01T00:00:00'
        self.data.loc[1,'timestamp']='2026-01-01T01:30:00Z'
        clean,report=clean_measurements(self.data)
        self.assertEqual(len(clean),2)

    def test_missing_column(self):
        with self.assertRaises(ValueError):
            clean_measurements(self.data.drop(columns='source'))


class GridTests(unittest.TestCase):
    def test_reference_topology(self):
        grid=synthetic_grid()
        graph=validate_grid(grid)
        self.assertEqual(len(graph),12)
        self.assertEqual(graph.number_of_edges(),12)
        self.assertEqual(grid_summary(grid)['balance_mw'],0)

    def test_invalid_endpoint_and_over_capacity(self):
        grid=synthetic_grid()
        grid['edges'][0]['target']='missing'
        with self.assertRaises(ValueError): validate_grid(grid)
        grid=synthetic_grid()
        grid['nodes'][0]['output_mw']=999
        with self.assertRaises(ValueError): validate_grid(grid)

    def test_duplicate_and_disconnected(self):
        grid=synthetic_grid()
        grid['nodes'].append(deepcopy(grid['nodes'][0]))
        with self.assertRaises(ValueError): validate_grid(grid)
        grid=synthetic_grid()
        grid['edges']=grid['edges'][1:]
        with self.assertRaises(ValueError): validate_grid(grid)

    def test_reset_isolation(self):
        source=synthetic_grid()
        one,two=GridEnvironment(source),GridEnvironment(source)
        one.topology['nodes'][0]['output_mw']=0
        self.assertEqual(two.topology['nodes'][0]['output_mw'],400)
        self.assertEqual(source['nodes'][0]['output_mw'],400)
        self.assertEqual(one.reset()['generation_mw'],700)
        observation,reward,terminated,info=one.step(Action.HOLD)
        self.assertEqual(observation['demand_mw'],700)
        self.assertIsInstance(reward,float)
        self.assertFalse(terminated)
        self.assertEqual(info['action'],'hold')


class DispatchTests(unittest.TestCase):
    def test_balanced(self):
        result=recommend(Observation(700,700,350))
        self.assertEqual(result['action'],'hold')
        self.assertFalse(result['executable'])

    def test_insufficient_reserve(self):
        result=recommend(Observation(900,700,50))
        self.assertEqual(result['requested_mw'],50)
        self.assertEqual(result['unmet_gap_mw'],150)
        self.assertFalse(result['feasible'])

    def test_surplus_requires_checks(self):
        self.assertFalse(recommend(Observation(500,700,50))['feasible'])

    def test_encoding_and_validation(self):
        self.assertEqual(encode_state(Observation(700,700,350)),(2,1,1,2,0))
        with self.assertRaises(ValueError): recommend(Observation(700,700,350,battery_soc=2))
        with self.assertRaises(ValueError): recommend(Observation(float('nan'),700,350))
        with self.assertRaises(ValueError): recommend(Observation(True,700,350))


class APITests(unittest.TestCase):
    def setUp(self):
        self.client=create_app({'TESTING':True}).test_client()

    def test_read_endpoints(self):
        for route in ['/api/health','/api/grid','/api/status','/api/measurements','/api/data/quality','/api/dispatch/baseline','/api/forecast','/api/openapi.json']:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code,200)
        self.assertEqual(self.client.get('/api/grid').json['summary']['nodes'],12)
        self.assertEqual(self.client.get('/api/health').json['phase'],2)
        self.assertEqual(self.client.get('/api/openapi.json').json['info']['version'],'0.2.0')
        modules=self.client.get('/api/status').json['modules']
        self.assertTrue(all('owner' not in module for module in modules))
        self.assertTrue(all(module['status']=='phase2_complete' for module in modules))

    def test_limits(self):
        for limit in ['-1','0','2161','abc']:
            self.assertEqual(self.client.get('/api/measurements?limit='+limit).status_code,400)
        self.assertEqual(self.client.get('/api/measurements?limit=2').json['count'],2)

    def test_post_validation(self):
        for body in [[],{}, {'demand_mw':'bad','generation_mw':0,'reserve_mw':0}, {'demand_mw':1,'generation_mw':0,'reserve_mw':0,'other':4}]:
            self.assertEqual(self.client.post('/api/dispatch/baseline',json=body).status_code,400)
        self.assertEqual(self.client.post('/api/dispatch/baseline',data='no').status_code,415)
        self.assertEqual(self.client.post('/api/dispatch/baseline',data='{',content_type='application/json').status_code,400)
        result=self.client.post('/api/dispatch/baseline',json={'demand_mw':800,'generation_mw':700,'reserve_mw':150})
        self.assertEqual(result.json['requested_mw'],100)
        self.assertEqual(result.json['data_source'],'user_supplied')

    def test_learned_dispatch_and_planned_explanation(self):
        dispatch=self.client.post('/api/dispatch',json={'demand_mw':800,'generation_mw':700,'reserve_mw':150})
        self.assertEqual(dispatch.status_code,200)
        self.assertFalse(dispatch.json['executable'])
        self.assertIn(dispatch.json['action'],[action.value for action in Action])
        self.assertEqual(self.client.post('/api/explain',json={}).status_code,501)

    def test_phase2_forecast_and_scenario(self):
        forecast=self.client.get('/api/forecast?model=autoregressive&target=solar_mw&horizon=3')
        self.assertEqual(forecast.status_code,200)
        self.assertEqual(len(forecast.json['predictions']),3)
        scenario=self.client.post('/api/scenario',json={'steps':3,'seed':7})
        self.assertEqual(scenario.status_code,200)
        self.assertEqual(scenario.json['steps'],3)
        self.assertEqual(len(scenario.json['trajectory']),3)
        self.assertEqual(scenario.json['data_source'],'synthetic')
        learned=self.client.post('/api/scenario',json={'steps':3,'seed':7,'policy':'q_learning'})
        self.assertEqual(learned.status_code,200)
        self.assertEqual(learned.json['policy'],'q_learning_phase2')

    def test_phase2_api_validation(self):
        for query in ['horizon=0','horizon=bad','target=bad','model=bad']:
            self.assertEqual(self.client.get('/api/forecast?'+query).status_code,400)
        invalid_scenarios=[
            [],
            {'steps':0},
            {'steps':2,'actions':['hold']},
            {'steps':1,'actions':['unknown']},
            {'steps':1,'faults':'bad'},
            {'steps':1,'faults':[{'step':0,'asset_id':'unknown'}]},
            {'steps':1,'unexpected':True},
            {'steps':1,'policy':'unknown'},
            {'steps':1,'policy':'baseline','actions':['hold']},
        ]
        for body in invalid_scenarios:
            with self.subTest(body=body):
                self.assertEqual(self.client.post('/api/scenario',json=body).status_code,400)
        self.assertEqual(self.client.post('/api/scenario',data='no').status_code,415)

    def test_missing_fixture(self):
        with TemporaryDirectory() as directory:
            client=create_app({'TESTING':True,'DATA_DIR':directory}).test_client()
            self.assertEqual(client.get('/api/grid').status_code,503)

    def test_page_and_unknown_route(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/api/no-such-route').status_code,404)


if __name__=='__main__':
    unittest.main()
