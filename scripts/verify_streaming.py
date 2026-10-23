"""Exercise actual Redis/PostgreSQL duplicate, crash replay and poison recovery."""
import json
import time
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from prism.streaming.store import connections,DurableStream,event


def main():
    r,db=connections();name='prism:verification:'+uuid4().hex;s=DurableStream(r,db,name);s.setup()
    asset='benchmark-'+uuid4().hex
    p=event(asset,datetime.now(timezone.utc).isoformat(),{'mw':-2},'https://example.org/synthetic-benchmark',source='synthetic_benchmark')
    first=s.publish(p);duplicate=s.publish(p)
    def crash(_):raise RuntimeError('simulated crash after PG commit')
    try:s.consume(before_ack=crash)
    except RuntimeError:pass
    pending=r.xpending(name,s.group)['pending']
    replay=DurableStream(r,db,name);replay.consume(consumer='restarted-worker',reclaim_ms=0)
    rows=replay.history(asset)
    r.xadd(name,{'event':'invalid json'});replay.consume()
    rejected=db.execute('SELECT count(*) FROM prism_rejected_events WHERE stream_id IN (SELECT stream_id FROM prism_rejected_events WHERE reason=%s)',('invalid_event',)).fetchone()[0]
    assert first==duplicate and pending==1 and len(rows)==1 and rejected>=1
    assert r.xpending(name,s.group)['pending']==0
    retention_name=name+':retention';retention=DurableStream(r,db,retention_name);retention.setup()
    old_ms=int(time.time()*1000)-7200000
    r.xadd(retention_name,{'event':json.dumps(p)},id=f'{old_ms}-0')
    assert retention.trim()==0 and r.xlen(retention_name)==1
    try:retention.consume(before_ack=crash)
    except RuntimeError:pass
    assert retention.trim()==0 and r.xlen(retention_name)==1
    retention.consume(reclaim_ms=0)
    r.xadd(retention_name,{'event':json.dumps(p)})
    retention.consume()
    assert retention.trim()==1
    r.delete(retention_name)
    result=dict(unread_retention_protected=True,pending_retention_protected=True,acknowledged_expiry_verified=True,duplicate_same_stream_id=True,committed_before_ack=True,pending_after_simulated_crash=pending,
        recovery_rows=len(rows),replay_idempotent=True,invalid_event_quarantined=True,health=replay.health())
    Path('reports/phase3_streaming.json').write_text(json.dumps(result,indent=2)+'\n')
    # Dedicated verification stream only; durable evidence rows retained and labeled synthetic.
    r.delete(name);db.close();r.close();print(json.dumps(result))

if __name__=='__main__':main()
