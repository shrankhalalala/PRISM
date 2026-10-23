"""HTTP verification against the actual composed stack; records scope and failures."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
from time import perf_counter,sleep
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from uuid import uuid4
import numpy as np


def call(path,body=None,authorized=False):
    headers={'Accept':'application/json'}
    if body is not None:headers['Content-Type']='application/json'
    if authorized:headers['X-PRISM-Operator-Token']=os.environ['PRISM_OPERATOR_TOKEN']
    request=Request('http://127.0.0.1:5053'+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    start=perf_counter()
    try:
        with urlopen(request,timeout=15) as response:return response.status,json.load(response),(perf_counter()-start)*1000
    except HTTPError as error:return error.code,json.load(error),(perf_counter()-start)*1000


def poll(identifier):
    for _ in range(300):
        status,job,_=call('/api/jobs/'+identifier)
        if job['status'] in {'succeeded','failed','cancelled'}:return job
        sleep(.1)
    raise RuntimeError('Job timeout')


def main():
    started=datetime.now(timezone.utc).isoformat();results={};probes={}
    for path in ['/api/readiness','/api/health','/api/reference-grid','/api/live/stations','/api/live/gridwatch','/api/operations/health','/api/forecast/real']:
        status,payload,elapsed=call(path);probes[path]={'status_code':status,'elapsed_ms':elapsed}
        assert status==200,(path,status)
        if path=='/api/readiness':results['model_initialization']=payload.get('model_initialization')
        if path=='/api/reference-grid':assert len(payload['assets'])==66 and len(payload['connections'])==261
        if path=='/api/live/stations':assert payload['transport']=='postgres_durable_history' and payload['coverage']['measured_assets']==49
    unauthorized,_,_=call('/api/jobs',{'kind':'scenario','request':{}});assert unauthorized==401
    status,job,_=call('/api/jobs',{'kind':'scenario','request':{'steps':8,'seed':42}},True);assert status==202
    completed=poll(job['id']);assert completed['status']=='succeeded' and completed['result']['execution']['containerized']
    status,forecast,_=call('/api/jobs',{'kind':'forecast','request':{}},True);assert status==202
    refreshed=poll(forecast['id']);assert refreshed['status']=='succeeded',refreshed
    code,review,_=call('/api/jobs',{'kind':'retrain','request':{}},True);assert code==202
    retrained=poll(review['id']);assert retrained['status']=='succeeded' and retrained['result']['test_used_for_promotion'] is False
    assert retrained['result']['execution']['containerized']
    body={'observation':{'demand_mw':500,'generation_mw':400,'reserve_mw':100},'valid_actions':['hold','increase_generation','discharge_battery']}
    latency={}
    for path,request in [('/api/explain',body),('/api/forecast/real',None),('/api/reference-grid',None),('/api/diagnose',{'dataset':'reference','alarms':[{'asset_id':'ss-pragati','observed_at':datetime.now(timezone.utc).isoformat()}]})]:
        samples=[];codes=[]
        for _ in range(21):
            code,payload,elapsed=call(path,request);samples.append(elapsed);codes.append(code)
            if path=='/api/diagnose' and code==200:assert payload['source_store']=='neo4j_verified_snapshot'
        latency[path]=dict(samples=21,first_http_ms_after_readiness=samples[0],warm_p50_ms=float(np.percentile(samples[1:],50)),warm_p95_ms=float(np.percentile(samples[1:],95)),max_ms=max(samples),failures=sum(code!=200 for code in codes))
        assert not latency[path]['failures']
    report=dict(started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),base_url='http://127.0.0.1:5053',
        probes=probes,operator_token_required=True,container_worker_verified=completed['result']['execution'],job_id=job['id'],
        recent_forecast_job_id=forecast['id'],recent_forecast_origin=refreshed['result']['origin'],retraining_job_id=review['id'],retraining_promoted=retrained['result']['promoted'],
        model_initialization=results.get('model_initialization'),latency=latency,limitation='Short local composed-stack verification, not a long-term uptime/load test. Model warmup occurs before readiness; measured requests include actual uncached explanations and Redis forecast cache. Startup initialization remains separately reported. No physical switching.')
    Path('reports/phase3_deployment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
