"""Validation-only candidate selection; preserve frozen baseline and test results."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import numpy as np
import pandas as pd
from prism.forecasting import LSTMForecaster, LSTMConfig, forecast_metrics
from prism.forecasting.direct import DirectDayAheadForecaster, load_autoregressive
from prism.forecasting.evaluation import origins, evaluate


def main():
    source=Path('data/processed/delhi_demand_hourly.csv')
    frame=pd.read_csv(source); digest=sha256(source.read_bytes()).hexdigest()
    a,b=int(len(frame)*.7),int(len(frame)*.85)
    train=frame.iloc[:a].dropna(subset=['demand_mw'])
    vi,ti=origins(frame,a,b),origins(frame,b,len(frame))
    models={'persistence':None,'baseline_ar':load_autoregressive('models/forecasting/phase3_demand_ar.json'), 'baseline_lstm':LSTMForecaster.load('models/forecasting/phase3_demand_lstm.json')}
    timings={};configs={}
    for ridge in (1.,100.):
        name=f'direct_ar_{ridge:g}';start=perf_counter()
        models[name]=DirectDayAheadForecaster(ridge=ridge).fit(train)
        timings[name]=perf_counter()-start
    for epochs, hidden in ((12,8),(24,8),(24,16)):
        name=f'seasonal_lstm_{epochs}_{hidden}';start=perf_counter()
        config=LSTMConfig(epochs=epochs,hidden_size=hidden,seasonal_residual=True)
        models[name]=LSTMForecaster(config).fit(train,'demand_mw')
        configs[name]=asdict(config);timings[name]=perf_counter()-start
        print('Trained',name,flush=True)
    av,pv=evaluate(frame,vi,models)
    validation={name:forecast_metrics(av,pv[name]) for name in models}
    selected=min(models,key=lambda n:validation[n]['rmse'])
    ar_name=min(['baseline_ar','direct_ar_1','direct_ar_100'],key=lambda n:validation[n]['rmse'])
    lstm_name=min(['baseline_lstm',*configs],key=lambda n:validation[n]['rmse'])
    output=Path('models/forecasting/refinement-2026-10-27');output.mkdir(exist_ok=True)
    # Save selection before inspecting the held-out cohort.
    selection=dict(selected=selected,autoregressive=ar_name,lstm=lstm_name,validation=validation,hourly_sha256=digest,test_used_for_selection=False)
    (output/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    at,pt=evaluate(frame,ti,models)
    test={name:forecast_metrics(at,pt[name]) for name in models}
    widths=np.quantile(np.abs(av-pv[selected]),.9,axis=0,method='higher')
    peak=float(at.max())
    for name,m in test.items():
        m.update(mae_percent_peak=100*m['mae']/peak,rmse_percent_peak=100*m['rmse']/peak)
        eligible=at>=1
        m.update(mape_percent=float(np.mean(np.abs(at[eligible]-pt[name][eligible])/at[eligible])*100),
                 mape_excluded=int((~eligible).sum()))
    report=dict(**selection,training_end=frame.timestamp.iloc[a-1],validation_end=frame.timestamp.iloc[b-1],test_end=frame.timestamp.iloc[-1],validation_origins=len(vi),test_origins=len(ti),test=test,configs=configs,training_seconds=timings,interval=dict(half_width_mw=widths.tolist(),heldout_coverage=float((abs(at-pt[selected])<=widths).mean()),nominal_coverage=.9,guarantee=False),limitation='Historical held-out cohort was reported previously; this is retrospective refinement, not a new prospective trial. Candidates fixed before this run; no test-based selection. Demand only.')
    Path('reports/phase3_forecast_refinement.json').write_text(json.dumps(report,indent=2)+'\n')
    metadata={'hourly_sha256':digest,'training_end':frame.timestamp.iloc[a-1]}
    models[lstm_name].save(output/'lstm.json',metadata=metadata)
    if ar_name.startswith('direct'):
        models[ar_name].save(output/'autoregressive.json',metadata)
    else:
        (output/'autoregressive.json').write_bytes(Path('models/forecasting/phase3_demand_ar.json').read_bytes())
    print(json.dumps(dict(selected=selected,validation=validation,test=test)),flush=True)

if __name__=='__main__':main()
