"""Validated Redis events, PostgreSQL idempotency, commit-before-ack recovery."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
import re
import time

STREAM = 'prism:measurements:v1'
GROUP = 'postgres-v1'
SCHEMA = '''
CREATE TABLE IF NOT EXISTS prism_measurements (
 event_id text PRIMARY KEY, source text NOT NULL, asset_id text NOT NULL,
 observed_at timestamptz NOT NULL, ingested_at timestamptz NOT NULL DEFAULT now(),
 payload jsonb NOT NULL);
CREATE INDEX IF NOT EXISTS prism_measurements_asset_time ON prism_measurements(asset_id, observed_at);
CREATE TABLE IF NOT EXISTS prism_collector_status (
 source_key text PRIMARY KEY, checked_at timestamptz NOT NULL, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS prism_rejected_events (
 stream_id text PRIMARY KEY, reason text NOT NULL, payload text NOT NULL,
 rejected_at timestamptz NOT NULL DEFAULT now());
'''
PUBLISH = '''
local existing = redis.call('GET', KEYS[2])
if existing then return existing end
if redis.call('XLEN', KEYS[1]) >= tonumber(ARGV[2]) then
 return redis.error_reply('ingestion_backpressure') end
local id = redis.call('XADD', KEYS[1], '*', 'event', ARGV[1])
redis.call('SET', KEYS[2], id, 'EX', 86400)
return id
'''


def event(asset_id, observed_at, values, source_url, source='delhi_sldc', context=None):
    """Canonical identity includes values: corrections are retained as revisions."""
    if not isinstance(asset_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',asset_id):
        raise ValueError('Invalid asset identifier')
    observed = datetime.fromisoformat(observed_at.replace('Z','+00:00'))
    if observed.tzinfo is None or observed.timestamp() > time.time()+120:
        raise ValueError('Invalid observation time')
    if source not in {'delhi_sldc','synthetic_benchmark'}:
        raise ValueError('Invalid source')
    if not isinstance(source_url,str) or not source_url.startswith('https://'):
        raise ValueError('HTTPS provenance required')
    if not isinstance(values,dict) or not values or len(values)>16:
        raise ValueError('Invalid measurements')
    clean={}
    allowed={'mw','mvar','voltage_kv','demand_mw','frequency_hz','drawal_mw','schedule_mw'}
    for key,value in values.items():
        if key not in allowed or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('Invalid finite measurement')
        if key not in {'mw','mvar'} and value<0:
            raise ValueError('Negative magnitude')
        if key=='frequency_hz' and not 40<=value<=60:
            raise ValueError('Invalid frequency')
        clean[key]=float(value)
    body=dict(schema_version='1.0',source=source,asset_id=asset_id,
              observed_at=observed.astimezone(timezone.utc).isoformat(),values=clean,source_url=source_url)
    if context is not None:
        if not isinstance(context,dict) or set(context)-{'measurement_role','source_label','mapping_dataset','quality_flags','source_status_raw'}:
            raise ValueError('Invalid measurement context')
        if len(json.dumps(context,allow_nan=False))>2000:
            raise ValueError('Context too large')
        body['context']=context
    body['event_id']=sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return body


def validate_event(payload):
    if not isinstance(payload,dict) or payload.get('schema_version')!='1.0':
        raise ValueError('Invalid event schema')
    expected=event(payload['asset_id'],payload['observed_at'],payload['values'],payload['source_url'],payload['source'],payload.get('context'))
    if expected!=payload:
        raise ValueError('Event checksum/schema mismatch')
    return expected


def connections():
    import redis
    import psycopg
    url=os.environ.get('PRISM_REDIS_URL')
    dsn=os.environ.get('PRISM_DATABASE_URL')
    if not url or not dsn:
        raise RuntimeError('Durable ingestion is not configured')
    return redis.Redis.from_url(url,decode_responses=True,socket_timeout=5,socket_connect_timeout=3), psycopg.connect(dsn,connect_timeout=3)


class DurableStream:
    def __init__(self, redis_client, database, stream=STREAM, group=GROUP):
        self.redis,self.db,self.stream,self.group=redis_client,database,stream,group

    def setup(self):
        self.db.execute(SCHEMA);self.db.commit()
        from redis.exceptions import ResponseError
        try:self.redis.xgroup_create(self.stream,self.group,id='0-0',mkstream=True)
        except ResponseError as exc:
            if 'BUSYGROUP' not in str(exc):raise

    def publish(self,payload):
        validate_event(payload)
        return self.redis.eval(PUBLISH,2,self.stream,'prism:dedup:'+self.stream+':'+payload['event_id'],
                               json.dumps(payload,sort_keys=True),100000)

    def consume(self,consumer='worker',count=100,reclaim_ms=30000,before_ack=None):
        # Recover crashed workers first; PG uniqueness makes replay safe after commit.
        claimed=self.redis.xautoclaim(self.stream,self.group,consumer,reclaim_ms,'0-0',count=count)
        records=claimed[1]
        if not records:
            batches=self.redis.xreadgroup(self.group,consumer,{self.stream:'>'},count=count,block=100)
            records=[record for _,items in batches for record in items]
        saved=0
        for sid,fields in records:
            try:
                payload=validate_event(json.loads(fields.get('event','null')))
            except (ValueError,KeyError,TypeError,AttributeError,OverflowError):
                self.db.execute('INSERT INTO prism_rejected_events(stream_id,reason,payload) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                                (sid,'invalid_event',json.dumps(fields)))
            else:
                from psycopg.types.json import Jsonb
                self.db.execute('INSERT INTO prism_measurements(event_id,source,asset_id,observed_at,payload) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                    (payload['event_id'],payload['source'],payload['asset_id'],payload['observed_at'],Jsonb(payload)))
                saved+=1
            self.db.commit()
            if before_ack:before_ack(sid)
            self.redis.xack(self.stream,self.group,sid)
        return saved

    def trim(self,now_ms=None):
        # Never trim unread or pending entries, including entries older than one hour.
        cutoff=int(now_ms if now_ms is not None else time.time()*1000)-3600000
        groups=self.redis.xinfo_groups(self.stream)
        floors=[int(g['last-delivered-id'].split('-')[0]) for g in groups]
        pending=self.redis.xpending(self.stream,self.group)
        if pending['min']:floors.append(int(pending['min'].split('-')[0]))
        threshold=min([cutoff,*floors])
        return self.redis.xtrim(self.stream,minid=f'{max(0,threshold)}-0',approximate=False)

    def history(self,asset_id,limit=100):
        if not isinstance(limit,int) or not 1<=limit<=1000:raise ValueError('limit must be 1..1000')
        return [row[0] for row in self.db.execute('SELECT payload FROM prism_measurements WHERE asset_id=%s ORDER BY observed_at DESC,event_id LIMIT %s',(asset_id,limit)).fetchall()]

    def health(self):
        self.redis.ping();self.db.execute('SELECT 1');self.db.commit()
        p=self.redis.xpending(self.stream,self.group)
        groups=self.redis.xinfo_groups(self.stream)
        lag=next((g.get('lag',0) for g in groups if g['name']==self.group),0)
        return dict(status='degraded' if p['pending'] or lag else 'ok',pending=p['pending'],unread=lag,
                    stream_length=self.redis.xlen(self.stream),retention_seconds=3600,
                    dedup_ttl_seconds=86400,acknowledgement='after_postgres_commit')
