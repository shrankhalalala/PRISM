"""Frozen-origin 24-hour demand forecasts; chronological 70/15/15 without gap bridging."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import resource
import numpy as np
import pandas as pd
from prism.forecasting import AutoregressiveForecaster,LSTMForecaster,LSTMConfig,forecast_metrics


def origins(frame,start,end,window=24,horizon=24):
    """Daily nonoverlapping targets; all 48 source hours must be observed."""
    stamps=pd.to_datetime(frame.timestamp,utc=True)
    result=[]
    for i in range(start,end-horizon+1,24):
        piece=frame.iloc[i-window:i+horizon]
        if len(piece)!=window+horizon or piece.demand_mw.isna().any():continue
        if (stamps.iloc[i+horizon-1]-stamps.iloc[i-window])!=pd.Timedelta(hours=window+horizon-1):continue
        result.append(i)
    return result


def evaluate(frame,indices,models):
    actual=[];predictions={name:[] for name in models}
    for i in indices:
        history=frame.iloc[i-24:i]
        actual.append(frame.demand_mw.iloc[i:i+24].to_numpy())
        for name,model in models.items():
            predictions[name].append(model.predict(history,24) if model else [float(history.demand_mw.iloc[-1])]*24)
    if not actual:raise ValueError('No eligible held-out 24-hour origins')
    return np.asarray(actual),{name:np.asarray(values) for name,values in predictions.items()}


def main():
    start=perf_counter();source=Path('data/processed/delhi_demand_hourly.csv');frame=pd.read_csv(source)
    train_end=int(len(frame)*.70);val_end=int(len(frame)*.85)
    train=frame.iloc[:train_end].dropna(subset=['demand_mw'])
    config=LSTMConfig();training_start=perf_counter()
    lstm=LSTMForecaster(config).fit(train,'demand_mw');training_seconds=perf_counter()-training_start
    ar=AutoregressiveForecaster(lags=24).fit(train,'demand_mw');models={'persistence':None,'autoregressive':ar,'lstm':lstm}
    val_indices=origins(frame,train_end,val_end);test_indices=origins(frame,val_end,len(frame))
    actual_val,pred_val=evaluate(frame,val_indices,models)
    actual_test,pred_test=evaluate(frame,test_indices,models)
    metrics={name:{'validation':forecast_metrics(actual_val,pred_val[name]),'test':forecast_metrics(actual_test,pred_test[name]),
        'test_by_horizon':[forecast_metrics(actual_test[:,h],pred_test[name][:,h]) for h in range(24)]} for name in models}
    selected=min(models,key=lambda name:metrics[name]['validation']['rmse'])
    # Validation-only absolute residual intervals, separately calibrated at each horizon.
    bands=np.quantile(np.abs(actual_val-pred_val[selected]),.9,axis=0,method='higher')
    covered=np.abs(actual_test-pred_test[selected])<=bands
    artifact=Path('models/forecasting/phase3_demand_lstm.json')
    checksum=sha256(source.read_bytes()).hexdigest()
    lstm.save(artifact,metadata={'data_source':'delhi_sldc','hourly_sha256':checksum,'training_end':frame.timestamp.iloc[train_end-1],'chronological_split':'70/15/15','forecast_horizon':24})
    arpath=Path('models/forecasting/phase3_demand_ar.json');arpath.write_text(json.dumps({'target':'demand_mw','lags':24,'coefficients':ar.coefficients.tolist(),'hourly_sha256':checksum},indent=2)+'\n')
    result=dict(data_source='delhi_sldc',target='demand_mw',hourly_sha256=checksum,
        split={'method':'chronological_70_15_15','training_calendar_hours':train_end,'validation_calendar_hours':val_end-train_end,'test_calendar_hours':len(frame)-val_end,
            'training_end':frame.timestamp.iloc[train_end-1],'validation_end':frame.timestamp.iloc[val_end-1],'test_end':frame.timestamp.iloc[-1]},
        protocol='frozen 24-hour recursive prediction at daily origins; no within-horizon actual values; incomplete 48-hour blocks excluded',
        validation_origins=len(val_indices),test_origins=len(test_indices),test_origin_timestamps=[frame.timestamp.iloc[i] for i in test_indices],
        model_config=asdict(config),lstm_training_seconds=training_seconds,total_seconds=perf_counter()-start,
        process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        rss_scope='macOS ru_maxrss bytes, entire evaluation process',metrics=metrics,
        selected_on_validation=selected,interval={'method':'validation absolute-residual 90th percentile per horizon','nominal_coverage':.9,'half_width_mw':bands.tolist(),
        'heldout_coverage':float(covered.mean()),'heldout_coverage_by_horizon':covered.mean(axis=0).tolist(),'guarantee':False},
        renewable_history_eligible=False,operationally_validated=False,
        limitation='Real Delhi demand only; no eligible real solar/wind history. Residual intervals are empirical and temporal distribution shift can reduce coverage. No electrical simulation validation.')
    Path('reports/phase3_real_forecasting.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['validation_origins','test_origins','selected_on_validation','lstm_training_seconds','total_seconds']}))

if __name__=='__main__':main()
