"""Read-only durable history and service health, with safe configuration failures."""
from flask import Blueprint,jsonify,request
from prism.streaming.store import connections,DurableStream

api=Blueprint('durable_history',__name__)


def inspect_store(callback):
    client=db=None
    try:
        client,db=connections()
        return jsonify(callback(DurableStream(client,db)))
    except Exception:
        return jsonify(status='unavailable',error='durable_store_unavailable',
                       message='Configure and start Redis/PostgreSQL and initialize the collector.'),503
    finally:
        if db is not None:db.close()
        if client is not None:client.close()


@api.get('/api/ingestion/health')
def ingestion_health():
    return inspect_store(lambda store:store.health())


@api.get('/api/history/<asset_id>')
def history(asset_id):
    try:limit=int(request.args.get('limit','100'))
    except ValueError:return jsonify(error='invalid_limit'),400
    if not 1<=limit<=1000:return jsonify(error='invalid_limit'),400
    return inspect_store(lambda store:dict(asset_id=asset_id,records=store.history(asset_id,limit),
        ordering='observed_at_desc',source='durable_events',limit=limit))
