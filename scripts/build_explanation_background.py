"""Reproduce 100 training-only background rows for interventional TreeSHAP."""
from hashlib import sha256
import json
from pathlib import Path
import random
import numpy as np
import pandas as pd
from prism.config import ROOT
from prism.grid.model import load_grid
from prism.simulation import Observation
from prism.dispatch.surrogate import FEATURES,MODEL,features
from scripts.train_surrogate import environment


def main():
    frame=pd.read_csv(ROOT/'data/processed/measurements.csv');grid=load_grid(ROOT/'data/raw/grid.json');rows=[]
    for day in range(63):
        env=environment(frame,grid,day);rng=random.Random(5000+day);obs=Observation(**env.reset(seed=5000+day))
        while True:
            valid=env.valid_actions();rows.append(features(obs,valid));raw,_,done,_=env.step(rng.choice(valid));obs=Observation(**raw)
            if done:break
    indices=np.random.default_rng(42).choice(len(rows),100,replace=False)
    payload=dict(features=list(FEATURES),rows=[rows[i] for i in indices],training_row_positions=indices.tolist(),
        sampling_seed=42,partition='training days 0..62; random-rollout seeds 5000..5062',
        surrogate_sha256=sha256(MODEL.read_bytes()).hexdigest())
    target=MODEL.parent/'background.json';target.write_text(json.dumps(payload,indent=2)+'\n');print('Saved 100 training-only background rows')

if __name__=='__main__':main()
