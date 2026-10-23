"""Shared bounded scenario runner for synchronous previews and durable jobs."""
from dataclasses import asdict
from pathlib import Path
import pandas as pd
from prism.config import ROOT,DATA_DIR
from prism.grid.model import load_grid
from prism.simulation import Action,Observation,GridEnvironment,SimulationConfig,quarter_hour_profile
from prism.dispatch.q_learning import QLearningAgent
from prism.dispatch.evaluation import baseline_action,q_action


class ScenarioCancelled(Exception):pass


def prepare_scenario(body,data_dir=DATA_DIR):
    if not isinstance(body,dict):raise ValueError('Expected a scenario object')
    unknown=set(body)-{'steps','seed','actions','faults','policy'}
    if unknown:raise ValueError('Unknown scenario fields: '+', '.join(sorted(unknown)))
    steps=body.get('steps',8);seed=body.get('seed',42);actions=body.get('actions');faults=body.get('faults',[]);policy=body.get('policy','baseline')
    if isinstance(steps,bool) or not isinstance(steps,int) or not 1<=steps<=96:raise ValueError('steps must be an integer between 1 and 96')
    if isinstance(seed,bool) or not isinstance(seed,int):raise ValueError('seed must be an integer')
    if actions is not None and (not isinstance(actions,list) or len(actions)!=steps):raise ValueError('actions must contain exactly one action per step')
    if not isinstance(faults,list):raise ValueError('faults must be an array')
    if policy not in {'baseline','q_learning'}:raise ValueError('policy must be baseline or q_learning')
    if actions is not None and 'policy' in body:raise ValueError('Provide actions or policy, not both')
    selected=[Action(value) for value in actions] if actions is not None else None
    learned=QLearningAgent.load(ROOT/'models/q_learning/phase2_policy.json') if policy=='q_learning' and selected is None else None
    frame=pd.read_csv(Path(data_dir)/'processed/measurements.csv')
    env=GridEnvironment(load_grid(Path(data_dir)/'raw/grid.json'),profile=quarter_hour_profile(frame,hours=24)[:steps],faults=faults,
        config=SimulationConfig(episode_steps=steps),seed=seed)
    return steps,seed,selected,learned,env


def run_scenario(body,data_dir=DATA_DIR,checkpoint=None):
    steps,seed,selected,learned,env=prepare_scenario(body,data_dir)
    trajectory=[];totals={key:0. for key in ['return','unserved_mwh','curtailed_mwh','operating_cost','emissions_kg']}
    observation=Observation(**env.reset(seed=seed))
    for index in range(steps):
        if checkpoint and index%4==0 and not checkpoint(index,steps):raise ScenarioCancelled()
        action=selected[index] if selected is not None else q_action(learned)(observation,env.valid_actions()) if learned else baseline_action(observation,env.valid_actions())
        raw,reward,terminated,info=env.step(action);trajectory.append(dict(observation=asdict(observation),reward=reward,**info))
        totals['return']+=reward
        for key in totals.keys()-{'return'}:totals[key]+=info['metrics'][key]
        observation=Observation(**raw)
        if terminated:break
    return dict(data_source='synthetic',policy='provided_actions' if selected is not None else 'q_learning_phase2' if learned else 'rule_based_prototype',
        seed=seed,steps=len(trajectory),totals={key:round(value,6) for key,value in totals.items()},final_observation=asdict(observation),trajectory=trajectory,
        assurance='Synthetic aggregate simulation; no AC/DC power flow or operational switching.')
