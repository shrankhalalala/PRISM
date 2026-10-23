"""Attribution and graph-hypothesis endpoints with explicit model/data boundaries."""
from flask import Blueprint,jsonify,request
from prism.dispatch.api import parse_advisory
from prism.explain.attribution import explain
from prism.explain.diagnosis import diagnose

api=Blueprint('explainability',__name__)


@api.post('/api/explain')
def explanation():
    if not request.is_json:return jsonify(error='invalid_request'),415
    try:observation,valid=parse_advisory(request.get_json())
    except (TypeError,ValueError) as exc:return jsonify(error='invalid_request',message=str(exc)),400
    try:return jsonify(explain(observation,valid))
    except (OSError,ImportError,ValueError):return jsonify(error='explanation_unavailable'),503


@api.post('/api/diagnose')
def diagnosis():
    if not request.is_json:return jsonify(error='invalid_request'),415
    try:return jsonify(diagnose(request.get_json()))
    except (TypeError,ValueError,KeyError,AttributeError) as exc:return jsonify(error='invalid_request',message=str(exc)),400
    except OSError:return jsonify(error='topology_unavailable'),503
