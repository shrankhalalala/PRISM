"""Weekly/drift candidate review; untouched baseline artifacts and test-independent gate."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from time import perf_counter
import numpy as np
import pandas as pd
from prism.config import ROOT
from prism.forecasting import AutoregressiveForecaster,LSTMForecaster,LSTMConfig,forecast_metrics
from prism.forecasting.registry import REGISTRY,active_bundle,promote,verify_bundle,bootstrap
from prism.forecasting.evaluation import origins,evaluate
from prism.forecasting.direct import DirectDayAheadForecaster,load_autoregressive


def history_frame():
    frozen=ROOT/'data/processed/delhi_demand_hourly.csv';base_hash=sha256(frozen.read_bytes()).hexdigest()
    audit=json.loads((ROOT/'reports/phase3_history_audit.json').read_text())
    if audit['hourly_sha256']!=base_hash:raise ValueError('Frozen source audit mismatch')
    frame=pd.read_csv(frozen);recent=ROOT/'artifacts/delhi_demand_recent.csv'
    if recent.exists():frame=pd.concat([frame,pd.read_csv(recent)],ignore_index=True)
    frame=frame.drop_duplicates('timestamp',keep='last');frame['timestamp']=pd.to_datetime(frame.timestamp,utc=True)
    frame=frame.sort_values('timestamp').set_index('timestamp')
    last=frame.demand_mw.last_valid_index()
    frame=frame.reindex(pd.date_range(frame.index.min(),last,freq='h')).rename_axis('timestamp').reset_index()
    frame['timestamp']=frame.timestamp.map(lambda stamp:stamp.isoformat())
    return frame,base_hash


def drift():
    frame,base_hash=history_frame();values=frame.demand_mw.dropna()
    baseline=pd.read_csv(ROOT/'data/processed/delhi_demand_hourly.csv').demand_mw.dropna()
    reference=baseline.iloc[:int(len(baseline)*.7)];recent=values.tail(168)
    if len(recent)<24:return dict(status='insufficient_data',trigger=False)
    shift=abs(float(recent.mean()-reference.mean()))/max(float(reference.std()),1.)
    return dict(status='measured',trigger=shift>2.,standardized_mean_shift=shift,threshold=2.,recent_hours=len(recent),base_hourly_sha256=base_hash,
        limitation='Season-sensitive mean-shift proxy, not measured forecast-error drift or proof that retraining will help.')


def load_incumbent():
    active=active_bundle()
    if active:
        report=active['report'];folder=active['folder'];name=report['selected_on_validation']
        lstm=folder/'lstm.json';ar=folder/'autoregressive.json'
    else:
        report=json.loads((ROOT/'reports/phase3_real_forecasting.json').read_text());name=report['selected_on_validation']
        lstm=ROOT/'models/forecasting/phase3_demand_lstm.json';ar=ROOT/'models/forecasting/phase3_demand_ar.json'
    if name=='lstm':return name,LSTMForecaster.load(lstm),report
    if name=='persistence':return name,None,report
    model=load_autoregressive(ar)
    return name,model,report


def retrain(checkpoint=None):
    start=perf_counter();bootstrap();frame,base_hash=history_frame()
    if frame.demand_mw.notna().sum()<1000:raise ValueError('Insufficient real training history')
    train_end=int(len(frame)*.70);val_end=int(len(frame)*.85);train=frame.iloc[:train_end].dropna(subset=['demand_mw'])
    config=LSTMConfig(seasonal_residual=True);lstm=LSTMForecaster(config).fit(train,'demand_mw')
    indices=origins(frame,train_end,val_end)
    variants={'recursive':AutoregressiveForecaster(lags=24).fit(train,'demand_mw'),
              'direct_day_ahead':DirectDayAheadForecaster(ridge=1.).fit(train,'demand_mw')}
    variant_actual,variant_predictions=evaluate(frame,indices,variants)
    ar_variant=min(variants,key=lambda name:forecast_metrics(variant_actual,variant_predictions[name])['rmse'])
    ar=variants[ar_variant]
    models={'persistence':None,'autoregressive':ar,'lstm':lstm}
    actual,pred=evaluate(frame,indices,models)
    metrics={name:{'validation':forecast_metrics(actual,pred[name])} for name in models};selected=min(models,key=lambda name:metrics[name]['validation']['rmse'])
    incumbent_name,incumbent,incumbent_report=load_incumbent()
    if pd.Timestamp(incumbent_report['split']['training_end'])>=pd.Timestamp(frame.timestamp.iloc[indices[0]]):raise ValueError('Incumbent overlaps validation origins')
    _,comparison=evaluate(frame,indices,{'incumbent':incumbent});incumbent_rmse=forecast_metrics(actual,comparison['incumbent'])['rmse']
    data_hash=sha256(frame.to_csv(index=False,float_format='%.6f').encode()).hexdigest()
    widths=np.quantile(np.abs(actual-pred[selected]),.9,axis=0,method='higher')
    report=dict(hourly_sha256=data_hash,base_hourly_sha256=base_hash,data_source='delhi_sldc',target='demand_mw',selected_on_validation=selected,
        split={'method':'chronological_70_15_15','training_end':frame.timestamp.iloc[train_end-1],'validation_end':frame.timestamp.iloc[val_end-1],'test_end':frame.timestamp.iloc[-1]},
        validation_origins=len(indices),test_reserved_hours=len(frame)-val_end,test_used_for_promotion=False,metrics=metrics,model_config=asdict(config),
        model_variants={'autoregressive':ar_variant,'lstm':'seasonal_residual'},
        interval={'method':'validation absolute-residual 90th percentile per horizon','nominal_coverage':.9,'half_width_mw':widths.tolist(),'guarantee':False},
        limitation='Real demand candidate; reserved test not used for promotion. Solar/wind and physical dispatch eligibility remain unavailable.')
    REGISTRY.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=REGISTRY,prefix='candidate-') as temporary:
        folder=Path(temporary);lstm.save(folder/'lstm.json',metadata={'hourly_sha256':data_hash,'training_end':report['split']['training_end']})
        if isinstance(ar,DirectDayAheadForecaster):
            ar.save(folder/'autoregressive.json',{'hourly_sha256':data_hash})
        else:
            (folder/'autoregressive.json').write_text(json.dumps({'target':'demand_mw','lags':24,'coefficients':ar.coefficients.tolist(),'hourly_sha256':data_hash},indent=2)+'\n')
        (folder/'forecast_report.json').write_text(json.dumps(report,indent=2)+'\n')
        hashes={path.name:sha256(path.read_bytes()).hexdigest() for path in folder.iterdir()};version=sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
        (folder/'manifest.json').write_text(json.dumps({'files':hashes},indent=2)+'\n');target=REGISTRY/version
        if not target.exists():folder.rename(target)
        else:verify_bundle(version)
    if checkpoint is not None and not checkpoint():
        return dict(version=version,promoted=False,cancelled=True,test_used_for_promotion=False)
    gate=promote(version,incumbent_rmse)
    result=dict(**gate,selected=selected,incumbent=incumbent_name,training_data_sha256=data_hash,
        drift=drift(),elapsed_seconds=perf_counter()-start,test_used_for_promotion=False)
    (REGISTRY/'last_review.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
