"""Labeled synthetic throughput; does not increase upstream polling rate."""
from datetime import datetime,timezone
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4
import numpy as np
from prism.streaming.store import connections,DurableStream,event


def main():
    r,db=connections();name='prism:benchmark:'+uuid4().hex;s=DurableStream(r,db,name);s.setup()
    asset='benchmark-'+uuid4().hex;stamp=datetime.now(timezone.utc).isoformat();latencies=[]
    start=perf_counter()
    for i in range(200):
        t=perf_counter();s.publish(event(asset,stamp,{'mw':float(i)},'https://example.org/synthetic-benchmark',source='synthetic_benchmark'));s.consume();latencies.append((perf_counter()-t)*1000)
    duration=perf_counter()-start
    result=dict(data_source='synthetic_benchmark',events=200,seconds=duration,events_per_second=200/duration,
        update_latency_ms={'p50':float(np.percentile(latencies,50)),'p95':float(np.percentile(latencies,95)),'max':max(latencies)},
        upstream_polling_increased=False,scope='local serial publish + PostgreSQL commit + acknowledgement')
    assert len(s.history(asset,1000))==200
    Path('reports/phase3_ingestion_benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
    r.delete(name);db.close();r.close();print(json.dumps(result))

if __name__=='__main__':main()
