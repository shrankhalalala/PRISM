"""Local advisory workflow with explicit production token and immutable decisions."""
from datetime import datetime,timezone
from functools import wraps
import hmac
import os
from uuid import UUID
from flask import Blueprint,current_app,jsonify,request
from prism.operations import store
from prism.simulation.runner import prepare_scenario
from prism.dispatch.api import parse_advisory
from prism.explain.attribution import explain
from prism.streaming.store import connections

api=Blueprint('operations',__name__)


def mutation(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        token=current_app.config.get('OPERATOR_TOKEN',os.environ.get('PRISM_OPERATOR_TOKEN',''))
        supplied=request.headers.get('X-PRISM-Operator-Token','')
        local=request.remote_addr in {'127.0.0.1','::1'} and os.environ.get('PRISM_ALLOW_LOCAL_OPERATOR','1')=='1'
        if (token and not hmac.compare_digest(supplied,token)) or (not token and not local):return jsonify(error='operator_authorization_required'),401
        if not request.is_json:return jsonify(error='invalid_request',message='Use application/json'),415
        return function(*args,**kwargs)
    return wrapped


def safe(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        try:
            for key in ('identifier',):
                if key in kwargs:kwargs[key]=str(UUID(kwargs[key]))
            return function(*args,**kwargs)
        except (ValueError,TypeError) as exc:return jsonify(error='invalid_request',message=str(exc)),400
        except Exception:return jsonify(error='operations_unavailable',message='Start configured PostgreSQL, Redis and the worker; initialize operations schema.'),503
    return wrapped


@api.get('/api/operations/health')
def health():
    services={'redis':'unavailable','postgres':'unavailable','worker':'unavailable'};client=db=None
    try:
        client,db=connections();db.execute('SELECT 1');db.commit();services['postgres']='ok'
        client.ping();services['redis']='ok';services['worker']='ok' if client.get('prism:worker:heartbeat') else 'unavailable'
    except Exception:pass
    finally:
        if db:db.close()
        if client:client.close()
    return jsonify(status='ok' if all(v=='ok' for v in services.values()) else 'degraded',services=services,advisory_only=True)


@api.post('/api/jobs')
@mutation
@safe
def create_job():
    body=request.get_json()
    if not isinstance(body,dict) or set(body)!={'kind','request'} or body['kind'] not in {'scenario','forecast'}:raise ValueError('Provide kind scenario/forecast and request')
    if body['kind']=='scenario':prepare_scenario(body['request'],current_app.config['DATA_DIR'])
    elif body['request']!={}:raise ValueError('Forecast request must be empty')
    key=request.headers.get('Idempotency-Key')
    if key and len(key)>100:raise ValueError('Idempotency key too long')
    job=store.create_job(body['kind'],body['request'],key)
    try:
        from prism.operations.tasks import run_job
        run_job.apply_async(args=[job['id']],retry=False)
    except Exception:job['dispatch_pending']=True
    return jsonify(job),202


@api.get('/api/jobs/<identifier>')
@safe
def get_job(identifier):
    job=store.get_job(identifier)
    return (jsonify(job),200) if job else (jsonify(error='not_found'),404)


@api.post('/api/jobs/<identifier>/cancel')
@mutation
@safe
def cancel_job(identifier):
    job=store.cancel_job(identifier)
    return (jsonify(job),200) if job else (jsonify(error='not_found'),404)


@api.post('/api/advisories')
@mutation
@safe
def advisory():
    body=request.get_json();observation,valid=parse_advisory(body)
    return jsonify(store.save_advisory(body,explain(observation,valid))),201


@api.get('/api/advisories/<identifier>/decisions')
@safe
def decisions(identifier):
    if store.advisory(identifier) is None:return jsonify(error='not_found'),404
    return jsonify(records=store.decisions(identifier))


@api.post('/api/advisories/<identifier>/decisions')
@mutation
@safe
def decision(identifier):
    row=store.append_decision(identifier,request.get_json())
    return (jsonify(row),201) if row else (jsonify(error='not_found'),404)


@api.get('/api/alerts')
def alerts():
    now=datetime.now(timezone.utc).isoformat();records=[]
    for name,client in [('aggregate',current_app.extensions['gridwatch']),('stations',current_app.extensions['stations'])]:
        snapshot=client.snapshot()
        if snapshot['status']!='live':records.append(dict(id=name+'-freshness',category='data_quality',severity='warning',message=f'{name.title()} measurements are {snapshot["status"]}; check source before interpreting values.',observed_at=now,data_source='delhi_sldc'))
        if name=='stations' and snapshot.get('unmatched_labels'):
            records.append(dict(id='unmapped-stations',category='mapping',severity='warning',message=f'{len(snapshot["unmatched_labels"])} source labels need mapping review.',observed_at=now,data_source='delhi_sldc'))
    try:
        with store.database() as db:
            jobs=db.execute("SELECT id,error_code,updated_at FROM prism_jobs WHERE status='failed' ORDER BY updated_at DESC LIMIT 10").fetchall()
        for job in jobs:records.append(dict(id=str(job['id']),category='job_failure',severity='warning',message='Background job failed: '+str(job['error_code']),observed_at=job['updated_at'].isoformat(),data_source='application'))
    except Exception:records.append(dict(id='history-unavailable',category='service',severity='warning',message='Durable operations history is unavailable.',observed_at=now,data_source='application'))
    return jsonify(alerts=records,checked_at=now,status='degraded' if records else 'ok',advisory_only=True,
        limitation='Data-quality and application alerts only; no inferred overload or grid fault without verified limits/measurements.')
