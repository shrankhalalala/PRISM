"""PostgreSQL durable jobs/outbox and append-only advisory decisions."""
from contextlib import contextmanager
from uuid import uuid4
from prism.streaming.store import connections

def Jsonb(value):
    from psycopg.types.json import Jsonb as wrap
    return wrap(value)

SCHEMA='''
CREATE TABLE IF NOT EXISTS prism_jobs (
 id uuid PRIMARY KEY, kind text NOT NULL, status text NOT NULL, request jsonb NOT NULL,
 result jsonb, error_code text, attempts integer NOT NULL DEFAULT 0,
 idempotency_key text UNIQUE, progress integer NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS prism_advisories (
 id uuid PRIMARY KEY, request jsonb NOT NULL, recommendation jsonb NOT NULL,
 data_source text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS prism_decisions (
 id uuid PRIMARY KEY, advisory_id uuid NOT NULL REFERENCES prism_advisories(id),
 decision text NOT NULL, chosen_action text NOT NULL, operator text NOT NULL,
 reason text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
'''


@contextmanager
def database():
    from psycopg.rows import dict_row
    r,db=connections();r.close();db.row_factory=dict_row
    try:yield db
    finally:db.close()


def initialize():
    with database() as db:db.execute(SCHEMA);db.commit()


def serialize(row):
    if row is None:return None
    result=dict(row)
    for key in ('id','advisory_id'):
        if result.get(key) is not None:result[key]=str(result[key])
    for key in ('created_at','updated_at'):
        if result.get(key) is not None:result[key]=result[key].isoformat()
    return result


def create_job(kind,request,key=None):
    with database() as db:
        identifier=str(uuid4())
        row=db.execute('INSERT INTO prism_jobs(id,kind,status,request,idempotency_key) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING RETURNING *',
            (identifier,kind,'queued',Jsonb(request),key)).fetchone()
        if row is None:
            row=db.execute('SELECT * FROM prism_jobs WHERE idempotency_key=%s',(key,)).fetchone()
            if row['kind']!=kind or row['request']!=request:raise ValueError('Idempotency key already used for another request')
        db.commit();return serialize(row)


def get_job(identifier):
    with database() as db:return serialize(db.execute('SELECT * FROM prism_jobs WHERE id=%s',(identifier,)).fetchone())


def cancel_job(identifier):
    with database() as db:
        db.execute("UPDATE prism_jobs SET status='cancelled',updated_at=now() WHERE id=%s AND status IN ('queued','running')",(identifier,));db.commit()
    return get_job(identifier)


def claim_job(identifier):
    with database() as db:
        row=db.execute("UPDATE prism_jobs SET status='running',attempts=attempts+1,updated_at=now() WHERE id=%s AND status='queued' AND attempts<3 RETURNING *",(identifier,)).fetchone();db.commit();return serialize(row)


def checkpoint(identifier,progress,total):
    with database() as db:
        row=db.execute("UPDATE prism_jobs SET progress=%s,updated_at=now() WHERE id=%s AND status='running' RETURNING id",(int(100*progress/total),identifier)).fetchone();db.commit();return row is not None


def finish(identifier,result=None,error=None,retry=False):
    with database() as db:
        db.execute("UPDATE prism_jobs SET status=%s,result=%s,error_code=%s,progress=%s,updated_at=now() WHERE id=%s AND status='running'",
            ('queued' if retry else 'failed' if error else 'succeeded',Jsonb(result) if result else None,error,0 if retry else 100,identifier));db.commit()


def recover_jobs():
    with database() as db:
        db.execute("UPDATE prism_jobs SET status=CASE WHEN attempts<3 THEN 'queued' ELSE 'failed' END,error_code='worker_lease_expired',updated_at=now() WHERE status='running' AND updated_at<now()-interval '10 minutes'")
        db.execute("UPDATE prism_jobs SET status='failed',error_code='retry_exhausted',updated_at=now() WHERE status='queued' AND attempts>=3")
        rows=db.execute("SELECT id FROM prism_jobs WHERE status='queued' ORDER BY created_at LIMIT 100").fetchall();db.commit();return [str(row['id']) for row in rows]


def save_advisory(body,recommendation):
    identifier=str(uuid4())
    with database() as db:
        db.execute('INSERT INTO prism_advisories(id,request,recommendation,data_source) VALUES (%s,%s,%s,%s)',
            (identifier,Jsonb(body),Jsonb(recommendation),'synthetic_policy_surrogate'));db.commit()
    return dict(id=identifier,recommendation=recommendation,data_source='synthetic_policy_surrogate',executable=False)


def advisory(identifier):
    with database() as db:return serialize(db.execute('SELECT * FROM prism_advisories WHERE id=%s',(identifier,)).fetchone())


def append_decision(identifier,body):
    from prism.simulation import Action
    original=advisory(identifier)
    if original is None:return None
    if not isinstance(body,dict) or set(body)-{'decision','override_action','operator','reason'}:raise ValueError('Invalid decision fields')
    decision=body.get('decision');reason=body.get('reason');operator=body.get('operator')
    if decision not in {'accept','override'}:raise ValueError('Choose accept or override')
    if any(not isinstance(v,str) or not v.strip() for v in (reason,operator)):raise ValueError('Operator and reason required')
    if len(reason)>2000 or len(operator)>100:raise ValueError('Decision text too long')
    if decision=='accept' and body.get('override_action'):raise ValueError('Accept cannot override action')
    chosen=Action(body.get('override_action')).value if decision=='override' else original['recommendation']['recommended_action']
    if chosen not in original['recommendation']['valid_actions']:raise ValueError('Action outside recorded advisory mask')
    with database() as db:
        row=db.execute('INSERT INTO prism_decisions(id,advisory_id,decision,chosen_action,operator,reason) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *',
            (str(uuid4()),identifier,decision,chosen,operator.strip(),reason.strip())).fetchone();db.commit()
    return dict(**serialize(row),executable=False)


def decisions(identifier):
    with database() as db:return [dict(**serialize(row),executable=False) for row in db.execute('SELECT * FROM prism_decisions WHERE advisory_id=%s ORDER BY created_at,id',(identifier,)).fetchall()]
