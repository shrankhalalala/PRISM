"""Exact interventional TreeSHAP for the selected surrogate raw-score class."""
from functools import lru_cache
from hashlib import sha256
import json
from time import perf_counter
import numpy as np
from prism.dispatch.api import get_surrogate
from prism.dispatch.surrogate import MODEL,FEATURES
from prism.dispatch.q_learning import ACTION_ORDER

BACKGROUND=MODEL.parent/'background.json'


@lru_cache(maxsize=2)
def _explainer(model_time,background_time):
    import shap
    model=get_surrogate();background=json.loads(BACKGROUND.read_text())
    if background['features']!=list(FEATURES) or background['surrogate_sha256']!=model.metadata['model_sha256'] or len(background['rows'])!=100:
        raise ValueError('Background/model mismatch')
    return shap.TreeExplainer(model.model,data=np.asarray(background['rows']),feature_names=list(FEATURES),
        feature_perturbation='interventional',model_output='raw')


def explain(observation,valid):
    import xgboost as xgb
    start=perf_counter();model=get_surrogate();prediction=model.predict(observation,valid)
    tree=_explainer(MODEL.stat().st_mtime_ns,BACKGROUND.stat().st_mtime_ns)
    row=np.asarray([list(prediction['features'].values())]);values=np.asarray(tree.shap_values(row,check_additivity=False))
    selected=next(i for i,a in enumerate(ACTION_ORDER) if a.value==prediction['surrogate_action'])
    if values.shape!=(1,len(FEATURES),6):raise ValueError('Unsupported SHAP shape')
    contributions=values[0,:,selected];base=float(np.asarray(tree.expected_value)[selected])
    raw=float(model.model.predict(xgb.DMatrix(row,feature_names=list(FEATURES)),output_margin=True)[0,selected])
    residual=raw-base-float(contributions.sum())
    if abs(residual)>1e-4:raise ValueError('Attribution additivity check failed')
    factors=[dict(feature=name,value=float(row[0,i]),contribution=float(contributions[i]),
        direction='increases' if contributions[i]>0 else 'decreases' if contributions[i]<0 else 'neutral',
        explanation=f"{name.replace('_',' ')} {'raises' if contributions[i]>0 else 'lowers' if contributions[i]<0 else 'does not change'} the surrogate raw score for {prediction['surrogate_action']}.") for i,name in enumerate(FEATURES)]
    return dict(**prediction,explained_action=prediction['surrogate_action'],explained_model='xgboost_surrogate',
        output_space='raw_margin',base_value=base,raw_margin=raw,additivity_residual=residual,
        factors=sorted(factors,key=lambda f:abs(f['contribution']),reverse=True),
        background_samples=100,background_sha256=sha256(BACKGROUND.read_bytes()).hexdigest(),
        method='interventional TreeSHAP',elapsed_ms=(perf_counter()-start)*1000,
        explanation_scope='Surrogate score only. A disagreement does not explain the Q-policy action; this is not physical causality.')
