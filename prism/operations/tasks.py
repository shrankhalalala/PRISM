"""Late-ack Celery jobs, durable outbox replay and hourly preview cycle."""
import os
from celery import Celery
from prism.operations import store
from prism.simulation.runner import run_scenario,ScenarioCancelled

celery=Celery('prism',broker=os.environ.get('PRISM_REDIS_URL','redis://127.0.0.1:6380/0'),backend=os.environ.get('PRISM_REDIS_URL','redis://127.0.0.1:6380/0'))
celery.conf.update(task_serializer='json',result_serializer='json',accept_content=['json'],timezone='UTC',
    task_acks_late=True,task_reject_on_worker_lost=True,worker_prefetch_multiplier=1,
    broker_connection_timeout=1,task_publish_retry=False,
    broker_transport_options={'socket_connect_timeout':1,'socket_timeout':1,'max_retries':0,'visibility_timeout':660},
    result_expires=86400,task_time_limit=600,task_soft_time_limit=540,broker_connection_retry_on_startup=True,
    beat_schedule={'recover-outbox':{'task':'prism.recover','schedule':30.},
                   'hourly-forecast':{'task':'prism.hourly_forecast','schedule':3600.}})


@celery.task(name='prism.run_job',acks_late=True,reject_on_worker_lost=True)
def run_job(identifier):
    job=store.claim_job(identifier)
    if job is None:return {'status':'already_claimed_or_terminal'}
    try:
        if job['kind']=='scenario':
            result=run_scenario(job['request'],checkpoint=lambda step,total:store.checkpoint(identifier,step,total))
        elif job['kind']=='forecast':
            from prism.data.recent import refresh_recent
            refresh_recent()
            from prism import create_app
            with create_app().test_client() as client:
                response=client.get('/api/forecast/real')
                if response.status_code!=200:raise ValueError('Forecast unavailable')
                result=response.get_json()
        else:raise ValueError('Unknown job kind')
        store.finish(identifier,result=result)
    except ScenarioCancelled:return {'status':'cancelled'}
    except Exception as exc:
        transient=not isinstance(exc,(ValueError,TypeError,FileNotFoundError))
        store.finish(identifier,error=type(exc).__name__,retry=transient and job['attempts']<3)
        return {'status':'retry_queued' if transient and job['attempts']<3 else 'failed'}
    return {'status':store.get_job(identifier)['status']}


@celery.task(name='prism.recover')
def recover():
    for identifier in store.recover_jobs():run_job.delay(identifier)
    return {'status':'dispatched'}


@celery.task(name='prism.hourly_forecast')
def hourly_forecast():
    from datetime import datetime,timezone
    key='hourly-forecast:'+datetime.now(timezone.utc).strftime('%Y-%m-%dT%H')
    job=store.create_job('forecast',{},key);run_job.delay(job['id']);return {'id':job['id']}

from celery.signals import heartbeat_sent,worker_ready

@heartbeat_sent.connect
@worker_ready.connect
def heartbeat(**_):
    try:
        import redis
        from datetime import datetime,timezone
        client=redis.Redis.from_url(celery.conf.broker_url,socket_timeout=1,socket_connect_timeout=1)
        client.setex('prism:worker:heartbeat',120,datetime.now(timezone.utc).isoformat());client.close()
    except Exception:pass
