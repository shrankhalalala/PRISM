"""Train richer-state policies with validation constraints; retain negative results."""
import json
from pathlib import Path
from hashlib import sha256
import statistics
import pandas as pd
from prism.dispatch.evaluation import load_scenario_suite,make_environment,baseline_action,q_action,run_policy
from prism.dispatch.q_learning import QLearningAgent,TrainingConfig
from prism.dispatch.refinement import StateAwareQLearningAgent
from prism.grid.model import load_grid


def main():
    topology=load_grid(Path('data/raw/grid.json'));frame=pd.read_csv('data/processed/measurements.csv')
    suite=load_scenario_suite('data/scenarios/phase2_scenarios.json')['scenarios']
    # Broaden training coverage within the original training period, retaining original held-out faults.
    training=[]
    for start in range(168,1104,48):
        training.append(dict(id=f'train-{start}',start_hour=start,steps=96,faults=[]))
    validation=[dict(id=f'val-{i}',start_hour=i,steps=96,faults=[]) for i in range(1200,1440,48)]
    validation += [s for s in suite if s['partition']=='validation']
    test=[s for s in suite if s['partition']=='test']
    seed=42
    def measure(agent, specs):
        policy=baseline_action if agent is None else q_action(agent)
        return [dict(id=s['id'],**run_policy(make_environment(topology,frame,s,seed),policy,seed)['totals']) for s in specs]
    def average(rows,key):return statistics.mean(r[key] for r in rows)
    baseline=measure(None,validation)
    candidates=[];agents={}
    for prior in (1.,5.):
        for training_seed in (11,23,42):
            name=f'prior-{prior:g}-seed-{training_seed}';counter=[0]
            def factory():
                s=training[counter[0]%len(training)];counter[0]+=1
                return make_environment(topology,frame,s,training_seed)
            agent=StateAwareQLearningAgent(TrainingConfig(episodes=300,seed=training_seed),prior=prior)
            history=agent.train(factory);rows=measure(agent,validation)
            # Savings are not accepted by increasing unserved energy or violations.
            eligible=all(r['unserved_mwh']<=b['unserved_mwh']+1e-6 and r['constraint_violations']<=b['constraint_violations'] for r,b in zip(rows,baseline))
            candidates.append(dict(name=name,validation=rows,eligible=eligible,validation_cost=average(rows,'operating_cost'),final_training_return=history[-1]['return']))
            agents[name]=agent
            print(name,'eligible',eligible,flush=True)
    eligible=[c for c in candidates if c['eligible'] and c['validation_cost']<average(baseline,'operating_cost')]
    selected=min(eligible,key=lambda c:c['validation_cost'])['name'] if eligible else 'baseline'
    # Lock before test inspection; save only best research candidate, not all trained tables.
    best=min(candidates,key=lambda c:(not c['eligible'],c['validation_cost']))['name']
    path=Path('models/q_learning/phase3_research_candidate.json')
    agents[best].save(path,dict(selected_on='validation safety then operating cost',name=best,accepted=selected==best,real_grid_eligible=False))
    inputs={name:sha256(Path(name).read_bytes()).hexdigest() for name in ['data/raw/grid.json','data/processed/measurements.csv','data/scenarios/phase2_scenarios.json','models/q_learning/phase2_policy.json']}
    report=dict(source='synthetic aggregate simulator',input_sha256=inputs,seeds=[11,23,42],episodes=300,training_start_hours=[s['start_hour'] for s in training],validation=baseline,candidates=candidates,selected_on_validation=selected,best_research_candidate=best,test_used_for_selection=False,policy_sha256=sha256(path.read_bytes()).hexdigest())
    output=Path('reports/phase3_dispatch_refinement.json');output.write_text(json.dumps(report,indent=2)+'\n')
    frozen=QLearningAgent.load('models/q_learning/phase2_policy.json')
    report['heldout']={name:measure(agent,test) for name,agent in [('baseline',None),('frozen_q',frozen),(best,agents[best])]}
    report['limitation']='Historical test scenarios previously reported; retrospective comparison only. Candidate is research-only; no automatic surrogate/SHAP replacement. Real-network dispatch remains ineligible without electrical parameters.'
    output.write_text(json.dumps(report,indent=2)+'\n');print('Selected:',selected,flush=True)

if __name__=='__main__':main()
