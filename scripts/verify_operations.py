"""Actual worker completion, durable replay/cancel and append-only advisory audit."""
import json
from pathlib import Path
from time import sleep
from uuid import uuid4
from prism import create_app
from prism.operations import store


def main():
    store.initialize();c=create_app({'TESTING':True}).test_client();key='verify-'+uuid4().hex
    body={'kind':'scenario','request':{'steps':8,'seed':42,'policy':'baseline'}}
    a=c.post('/api/jobs',json=body,headers={'Idempotency-Key':key});assert a.status_code==202,a.json
    b=c.post('/api/jobs',json=body,headers={'Idempotency-Key':key});assert a.json['id']==b.json['id']
    identifier=a.json['id']
    for _ in range(100):
        job=c.get('/api/jobs/'+identifier).json
        if job['status'] in {'succeeded','failed'}:break
        sleep(.1)
    assert job['status']=='succeeded',job
    assert job['result']['data_source']=='synthetic' and job['result']['steps']==8
    cancelled=store.create_job('scenario',{'steps':8},'cancel-'+uuid4().hex);store.cancel_job(cancelled['id'])
    from prism.operations.tasks import run_job
    assert run_job(cancelled['id'])['status']=='already_claimed_or_terminal'
    advisory=c.post('/api/advisories',json={'observation':{'demand_mw':500,'generation_mw':400,'reserve_mw':100},'valid_actions':['hold','increase_generation']})
    assert advisory.status_code==201,advisory.json
    aid=advisory.json['id'];actions=['hold','increase_generation'];recommended=advisory.json['recommendation']['recommended_action']
    # These are labeled software-verification records, not human operational acceptance.
    first=c.post('/api/advisories/'+aid+'/decisions',json={'decision':'accept','operator':'software-verification','reason':'Synthetic workflow test; not an operational decision.'})
    second=c.post('/api/advisories/'+aid+'/decisions',json={'decision':'override','override_action':next(a for a in actions if a!=recommended),'operator':'software-verification','reason':'Synthetic override audit test; no equipment command.'})
    assert first.status_code==201 and second.status_code==201
    history=c.get('/api/advisories/'+aid+'/decisions').json['records'];assert len(history)==2 and not history[0]['executable']
    secured=create_app({'TESTING':True,'OPERATOR_TOKEN':'verification-only-token'}).test_client()
    assert secured.post('/api/jobs',json=body).status_code==401
    result=dict(job_id=identifier,worker_completion=job['status'],duplicate_request_same_id=True,
        cancelled_job_not_executed=True,advisory_id=aid,append_only_decision_records=len(history),
        explicit_software_verification_records=True,operator_token_rejection_verified=True,
        advisory_only=True,health=c.get('/api/operations/health').json)
    Path('reports/phase3_operations.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
