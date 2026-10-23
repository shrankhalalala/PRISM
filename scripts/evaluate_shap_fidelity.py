"""Declared held-out permutation/attribution ranking probe; retains poor correlation."""
import json
from pathlib import Path
import random
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import xgboost as xgb
from prism.config import ROOT
from prism.dispatch.api import get_surrogate
from prism.dispatch.surrogate import FEATURES,features
from prism.dispatch.q_learning import ACTION_ORDER
from prism.explain.attribution import _explainer,BACKGROUND,MODEL
from prism.simulation import Observation
from scripts.train_surrogate import environment
from prism.grid.model import load_grid


def main():
    frame=pd.read_csv(ROOT/'data/processed/measurements.csv');grid=load_grid(ROOT/'data/raw/grid.json');model=get_surrogate();rows=[];labels=[]
    for day in range(76,90):
        env=environment(frame,grid,day);rng=random.Random(5000+day);obs=Observation(**env.reset(seed=5000+day))
        while True:
            valid=env.valid_actions();rows.append(features(obs,valid));labels.append(ACTION_ORDER.index(model.policy.action(obs,valid)))
            raw,_,done,_=env.step(rng.choice(valid));obs=Observation(**raw)
            if done:break
    rng=np.random.default_rng(42);selected=rng.choice(len(rows),100,replace=False);values=np.asarray(rows)[selected];labels=np.asarray(labels)[selected]
    tree=_explainer(MODEL.stat().st_mtime_ns,BACKGROUND.stat().st_mtime_ns)
    attribution=np.abs(np.asarray(tree.shap_values(values,check_additivity=False))).mean(axis=(0,2))
    def loss(x):
        p=model.model.predict(xgb.DMatrix(x,feature_names=list(FEATURES)))
        return -float(np.log(np.maximum(p[np.arange(len(labels)),labels],1e-12)).mean())
    baseline=loss(values);effects=[];deviations=[]
    for feature in range(len(FEATURES)):
        changes=[]
        for _ in range(5):
            permuted=values.copy();permuted[:,feature]=rng.permutation(permuted[:,feature]);changes.append(loss(permuted)-baseline)
        effects.append(float(np.mean(changes)));deviations.append(float(np.std(changes)))
    correlation=float(spearmanr(attribution,effects).statistic)
    report=dict(protocol='Spearman correlation across ten features between mean absolute raw-score SHAP (all six classes) and mean increase in Q-label log loss after independent feature permutation',
        heldout_episode_days=[76,89],sampled_states=100,seed=42,permutation_repeats=5,background_samples=100,
        mean_absolute_shap=dict(zip(FEATURES,attribution.tolist())),permutation_logloss_increase=dict(zip(FEATURES,effects)),permutation_repeat_std=dict(zip(FEATURES,deviations)),
        spearman_correlation=correlation,target_strictly_greater_than=.85,target_met=correlation>.85,
        limitation='Ranking probe only. Correlated/derived features and action masks create off-manifold permutations; this is not a universal SHAP fidelity guarantee, local causal test or operator trust measurement.')
    Path('reports/phase3_shap_fidelity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'spearman_correlation':correlation,'target_met':correlation>.85}))

if __name__=='__main__':main()
