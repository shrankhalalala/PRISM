"""Advisory surrogate API; never sends equipment commands."""
from functools import lru_cache
from flask import Blueprint,jsonify,request
from prism.dispatch.surrogate import Surrogate,MODEL,POLICY,features
from prism.simulation import Observation,Action

api=Blueprint('surrogate',__name__)


@lru_cache(maxsize=2)
def _load_surrogate(model_time,metadata_time,policy_time):
    return Surrogate()


def get_surrogate():
    return _load_surrogate(MODEL.stat().st_mtime_ns,MODEL.with_suffix('.metadata.json').stat().st_mtime_ns,POLICY.stat().st_mtime_ns)


def parse_advisory(body):
    if not isinstance(body,dict) or set(body)!={'observation','valid_actions'}:
        raise ValueError('Provide observation and valid_actions')
    if not isinstance(body['observation'],dict) or not isinstance(body['valid_actions'],list):raise ValueError('Invalid advisory inputs')
    observation=Observation(**body['observation']);valid=tuple(Action(a) for a in body['valid_actions'])
    features(observation,valid)
    return observation,valid


@api.post('/api/dispatch/surrogate')
def surrogate_dispatch():
    if not request.is_json:return jsonify(error='invalid_request',message='Use application/json'),415
    try:
        observation,valid=parse_advisory(request.get_json())
    except (ValueError,TypeError) as exc:return jsonify(error='invalid_request',message=str(exc)),400
    try:return jsonify(get_surrogate().predict(observation,valid))
    except (OSError,ImportError,ValueError):return jsonify(error='surrogate_unavailable'),503
