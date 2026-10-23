"""Episode/chronology-separated six-action surrogate and paired synthetic evaluation."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import random
from time import perf_counter
import numpy as np
import pandas as pd
import xgboost as xgb
from prism.config import ROOT
from prism.grid.model import load_grid
from prism.simulation import Action,Observation,GridEnvironment,SimulationConfig,quarter_hour_profile
from prism.dispatch.q_learning import QLearningAgent,ACTION_ORDER
from prism.dispatch.surrogate import FEATURES,MODEL,POLICY,Surrogate,features
from prism.dispatch.evaluation import run_policy,baseline_action,q_action


def environment(frame,grid,day):
    faults=[] if day%3==0 else [dict(step=32,asset_id='gas' if day%3==1 else 'line_11',duration_steps=16)]
    return GridEnvironment(grid,profile=quarter_hour_profile(frame.iloc[day*24:(day+1)*24],hours=24),faults=faults,
        config=SimulationConfig(episode_steps=96),seed=5000+day)


def main():
    started=perf_counter();frame=pd.read_csv(ROOT/'data/processed/measurements.csv');grid=load_grid(ROOT/'data/raw/grid.json');policy=QLearningAgent.load(POLICY)
    records={part:[] for part in ['train','validation','test']};labels={p:[] for p in records};masks={p:[] for p in records}
    for day in range(90):
        part='train' if day<63 else 'validation' if day<76 else 'test';rng=random.Random(5000+day)
        env=environment(frame,grid,day);obs=Observation(**env.reset(seed=5000+day))
        while True:
            valid=env.valid_actions();records[part].append(features(obs,valid));labels[part].append(ACTION_ORDER.index(policy.action(obs,valid)));masks[part].append(valid)
            raw,_,done,_=env.step(rng.choice(valid));obs=Observation(**raw)
            if done:break
    matrices={p:xgb.DMatrix(np.asarray(records[p]),label=labels[p],feature_names=list(FEATURES)) for p in records}
    candidates=[]
    for depth in (3,5):
        model=xgb.train(dict(objective='multi:softprob',num_class=6,max_depth=depth,eta=.1,seed=42,nthread=2,eval_metric='mlogloss'),
            matrices['train'],num_boost_round=150,evals=[(matrices['validation'],'validation')],early_stopping_rounds=15,verbose_eval=False)
        model=model[:model.best_iteration+1]
        predictions=model.predict(matrices['validation']);loss=-float(np.log(np.maximum(predictions[np.arange(len(labels['validation'])),labels['validation']],1e-12)).mean())
        candidates.append((loss,depth,model))
    loss,depth,model=min(candidates,key=lambda candidate:candidate[0]);MODEL.parent.mkdir(parents=True,exist_ok=True);model.save_model(MODEL)
    metadata=dict(features=list(FEATURES),actions=[a.value for a in ACTION_ORDER],q_policy_sha256=sha256(POLICY.read_bytes()).hexdigest(),
        model_sha256=sha256(MODEL.read_bytes()).hexdigest(),source='synthetic_seed_42',seed=42,max_depth=depth,rounds=model.num_boosted_rounds(),
        split='63/13/14 complete chronological day episodes; seeds 5000..5089; no overlapping episodes/windows',
        threshold=.75,calibration='uncalibrated softprob score; abstain below threshold',
        feature_limit='Six observed fields plus imbalance, generation/demand ratio, reserve/demand ratio and supplied valid-action bitmask. Does not invent coal/gas available MW.')
    MODEL.with_suffix('.metadata.json').write_text(json.dumps(metadata,indent=2)+'\n');surrogate=Surrogate()
    report=dict(**metadata,training_rows=len(labels['train']),validation_rows=len(labels['validation']),test_rows=len(labels['test']),fidelity={})
    for part in ('train','validation','test'):
        probabilities=model.predict(matrices[part]);predicted=[];scores=[]
        for probs,valid in zip(probabilities,masks[part]):
            i=max((ACTION_ORDER.index(a) for a in valid),key=lambda i:(probs[i],-i));predicted.append(i);scores.append(float(probs[i]))
        expected=np.asarray(labels[part]);predicted=np.asarray(predicted);accepted=np.asarray(scores)>=.75
        confusion=np.zeros((6,6),dtype=int)
        for y,p in zip(expected,predicted):confusion[y,p]+=1
        report['fidelity'][part]=dict(agreement=float((predicted==expected).mean()),
            accepted_fraction=float(accepted.mean()),accepted_agreement=float((predicted[accepted]==expected[accepted]).mean()) if accepted.any() else None,
            action_support={a.value:int((expected==i).sum()) for i,a in enumerate(ACTION_ORDER)},confusion_matrix=confusion.tolist())
    paired=[]
    for day in range(76,90):
        outcomes={}
        for name,choose in [('baseline',baseline_action),('q_learning',q_action(policy)),('surrogate',lambda obs,valid:Action(surrogate.predict(obs,valid)['surrogate_action']))]:
            outcomes[name]=run_policy(environment(frame,grid,day),choose,5000+day)['totals']
        paired.append(dict(day=day,seed=5000+day,outcomes=outcomes))
    report.update(paired_test_episodes=paired,elapsed_seconds=perf_counter()-started,
        limitation='Synthetic aggregate dynamics only; no real-grid electrical eligibility. Policy performance and surrogate fidelity are separate. Missing action support is not evidence for that class. No claim of improved Phase 2 Q-policy.')
    Path('reports/phase3_surrogate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'test':report['fidelity']['test'],'elapsed_seconds':report['elapsed_seconds']}))

if __name__=='__main__':main()
