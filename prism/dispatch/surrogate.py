"""Six-action XGBoost surrogate of a frozen synthetic Q-policy."""
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from prism.config import ROOT
from prism.dispatch.baseline import encode_state
from prism.dispatch.q_learning import ACTION_ORDER,QLearningAgent
from prism.simulation import Observation,Action

FEATURES=('demand_mw','generation_mw','reserve_mw','battery_soc','renewable_trend','fault_present',
          'imbalance_mw','generation_demand_ratio','reserve_demand_ratio','valid_action_mask')
MODEL=ROOT/'models/surrogate/phase3_xgboost.json'
POLICY=ROOT/'models/q_learning/phase2_policy.json'


def features(observation,valid_actions):
    encode_state(observation)
    valid=tuple(Action(v) for v in valid_actions)
    if not valid or len(set(valid))!=len(valid):raise ValueError('Require distinct valid actions')
    demand=max(observation.demand_mw,1.)
    values=[observation.demand_mw,observation.generation_mw,observation.reserve_mw,observation.battery_soc,
        observation.renewable_trend,float(observation.fault_present),observation.demand_mw-observation.generation_mw,
        observation.generation_mw/demand,observation.reserve_mw/demand,
        sum(1<<ACTION_ORDER.index(action) for action in valid)]
    if not np.isfinite(values).all():raise ValueError('Invalid features')
    return values


class Surrogate:
    def __init__(self,path=MODEL,policy_path=POLICY):
        import xgboost as xgb
        self.path=Path(path);self.metadata=json.loads(self.path.with_suffix('.metadata.json').read_text())
        if self.metadata['features']!=list(FEATURES) or self.metadata['actions']!=[a.value for a in ACTION_ORDER]:raise ValueError('Surrogate schema mismatch')
        if self.metadata['q_policy_sha256']!=sha256(Path(policy_path).read_bytes()).hexdigest():raise ValueError('Q-policy version mismatch')
        if self.metadata['model_sha256']!=sha256(self.path.read_bytes()).hexdigest():raise ValueError('Model integrity mismatch')
        self.model=xgb.Booster();self.model.load_model(self.path)
        self.policy=QLearningAgent.load(policy_path)

    def predict(self,observation,valid_actions):
        import xgboost as xgb
        valid=tuple(Action(a) for a in valid_actions);row=features(observation,valid)
        p=self.model.predict(xgb.DMatrix(np.asarray([row]),feature_names=list(FEATURES)))[0]
        index=max((ACTION_ORDER.index(a) for a in valid),key=lambda i:(p[i],-i))
        q=self.policy.action(observation,valid)
        score=float(p[index]);surrogate=ACTION_ORDER[index]
        return dict(q_action=q.value,surrogate_action=surrogate.value,recommended_action=q.value,
            probabilities={a.value:float(p[i]) for i,a in enumerate(ACTION_ORDER)},score=score,
            agreement=q==surrogate,abstained=score<.75,threshold=.75,calibrated_probability=False,
            valid_actions=[a.value for a in valid],features=dict(zip(FEATURES,row)),
            q_policy_sha256=self.metadata['q_policy_sha256'],surrogate_sha256=self.metadata['model_sha256'],
            data_source='synthetic_policy_surrogate',executable=False,
            limitation='Surrogate fidelity is agreement with a frozen synthetic policy, not operator trust or real-grid dispatch quality. Recommendation remains the Q-policy action; caller-supplied masks require independent feasibility checks.')
