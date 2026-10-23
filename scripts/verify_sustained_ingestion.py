"""60-second controlled synthetic ingestion at 20 events/s; zero upstream requests."""
from datetime import datetime,timezone
import json
from pathlib import Path
from time import perf_counter,sleep
from uuid import uuid4
import numpy as np
from prism.streaming.store import connections,DurableStream,event


def main():
    r,db=connections();name='prism:sustained:'+uuid4().hex;store=DurableStream(r,db,name);store.setup()
    asset='benchmark-'+uuid4().hex;stamp=datetime.now(timezone.utc).isoformat();duration=60.;rate=20;latency=[];failed=0
    started=perf_counter()
    for i in range(int(duration*rate)):
        wait=started+i/rate-perf_counter()
        if wait>0:sleep(wait)
        tick=perf_counter()
        try:
            store.publish(event(asset,stamp,{'mw':float(i)},'https://example.org/synthetic-benchmark',source='synthetic_benchmark'));store.consume()
            latency.append((perf_counter()-tick)*1000)
        except Exception:
            failed+=1;db.rollback()
    remaining=started+duration-perf_counter()
    if remaining>0:sleep(remaining)
    elapsed=perf_counter()-started
    count=db.execute('SELECT count(*) FROM prism_measurements WHERE asset_id=%s',(asset,)).fetchone()[0]
    health=store.health()
    report=dict(data_source='synthetic_benchmark',scheduled_rate_per_second=rate,duration_seconds=elapsed,
        attempted=int(duration*rate),persisted=count,failed=failed,dropped=1200-count-failed,
        persisted_events_per_second=count/elapsed,latency_ms={'p50':float(np.percentile(latency,50)),'p95':float(np.percentile(latency,95)),'max':max(latency)},
        final_pending=health['pending'],final_unread=health['unread'],upstream_requests=0,
        scope='Single local producer/consumer, 60 seconds at controlled20 events/s; serial Redis publication through PostgreSQL commit/ack. Not saturation capacity or long-term availability.')
    Path('reports/phase3_ingestion_sustained.json').write_text(json.dumps(report,indent=2)+'\n')
    r.delete(name);db.close();r.close();assert count==1200 and failed==0 and health['pending']==0 and health['unread']==0
    print(json.dumps(report))

if __name__=='__main__':main()
