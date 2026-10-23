"""Real demand forecasts with immutable history/model provenance and gap gates."""
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from flask import Blueprint,jsonify,request
from prism.config import ROOT
from prism.forecasting import AutoregressiveForecaster,LSTMForecaster
from prism.forecasting.models import require_recent_window

api=Blueprint('real_forecasting',__name__)


@api.get('/api/forecast/real')
def real_forecast():
    target=request.args.get('target','demand_mw')
    if target not in {'demand_mw','solar_mw','wind_mw'}:return jsonify(error='invalid_target'),400
    if target!='demand_mw':return jsonify(error='real_history_unavailable',target=target,eligible=False),422
    try:
        source=ROOT/'data/processed/delhi_demand_hourly.csv';raw=source.read_bytes();data_hash=sha256(raw).hexdigest()
        report=json.loads((ROOT/'reports/phase3_real_forecasting.json').read_text())
        if report['hourly_sha256']!=data_hash:raise ValueError('Forecast/data version mismatch')
        model=request.args.get('model',report['selected_on_validation'])
        if model not in {'persistence','autoregressive','lstm'}:return jsonify(error='invalid_model'),400
        frame=pd.read_csv(source).dropna(subset=['demand_mw'])
        recent=ROOT/'artifacts/delhi_demand_recent.csv';context_hash=data_hash
        if recent.exists():
            recent_raw=recent.read_bytes();context_hash=sha256(raw+recent_raw).hexdigest()
            recent_frame=pd.read_csv(recent).dropna(subset=['demand_mw'])
            frame=pd.concat([frame,recent_frame],ignore_index=True).drop_duplicates('timestamp',keep='last').sort_values('timestamp')
        history=frame.tail(24);require_recent_window(history,24)
        stamp=pd.Timestamp(history.timestamp.iloc[-1]);age=max(0,(datetime.now(timezone.utc)-stamp.to_pydatetime()).total_seconds())
        if model=='lstm':
            artifact=ROOT/'models/forecasting/phase3_demand_lstm.json'
        elif model=='autoregressive':artifact=ROOT/'models/forecasting/phase3_demand_ar.json'
        else:artifact=ROOT/'reports/phase3_real_forecasting.json'
        artifact_hash=sha256(artifact.read_bytes()).hexdigest()
        key='prism:forecast:'+context_hash+':'+artifact_hash+':'+model
        cached=None;client=None
        if os.environ.get('PRISM_REDIS_URL'):
            try:
                import redis
                client=redis.Redis.from_url(os.environ['PRISM_REDIS_URL'],socket_timeout=1,socket_connect_timeout=1)
                cached=client.get(key)
            except Exception:client=None
        if cached:predictions=json.loads(cached)
        else:
            if model=='lstm':
                meta=json.loads(artifact.read_text())['metadata']
                if meta['hourly_sha256']!=data_hash:raise ValueError('Model/history mismatch')
                predictions=LSTMForecaster.load(artifact).predict(history,24)
            elif model=='autoregressive':
                payload=json.loads(artifact.read_text())
                if payload['hourly_sha256']!=data_hash:raise ValueError('Model/history mismatch')
                fitted=AutoregressiveForecaster(lags=24);fitted.target=target;fitted.coefficients=np.asarray(payload['coefficients']);predictions=fitted.predict(history,24)
            else:predictions=[float(history.demand_mw.iloc[-1])]*24
            if client:
                try:client.setex(key,86400,json.dumps(predictions))
                except Exception:pass
        if client:client.close()
        interval=None
        if model==report['selected_on_validation']:
            widths=report['interval']['half_width_mw']
            interval={'method':report['interval']['method'],'nominal_coverage':.9,'guarantee':False,
                'lower_mw':[max(0,p-w) for p,w in zip(predictions,widths)],'upper_mw':[p+w for p,w in zip(predictions,widths)]}
        return jsonify(target=target,data_source='delhi_sldc',model=model,horizon_hours=24,predictions=predictions,
            forecast_timestamps=[(stamp+pd.Timedelta(hours=h)).isoformat() for h in range(1,25)],
            origin=stamp.isoformat(),source_age_seconds=age,status='stale_historical_preview' if age>7200 else 'recent_history_preview',
            hourly_sha256=data_hash,history_context_sha256=context_hash,artifact_sha256=artifact_hash,training_end=report['split']['training_end'],interval=interval,
            executable=False,limitation=report['limitation'],cache_ttl_seconds=86400,cache_hit=bool(cached))
    except (OSError,ValueError,KeyError,TypeError):
        return jsonify(error='real_forecast_unavailable',message='Prepare audited history and train matching models; the latest 24-hour input must be complete.'),503
