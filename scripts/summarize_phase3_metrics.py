"""Report-normalized demand metrics and paired synthetic outcomes; no target rewriting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prism.config import ROOT
from prism.forecasting import LSTMForecaster,AutoregressiveForecaster,forecast_metrics


def main():
    report=json.loads((ROOT/'reports/phase3_real_forecasting.json').read_text());frame=pd.read_csv(ROOT/'data/processed/delhi_demand_hourly.csv')
    times=pd.to_datetime(frame.timestamp,utc=True);lookup={t:i for i,t in enumerate(times)}
    ar=AutoregressiveForecaster();ar.target='demand_mw';ar.coefficients=np.asarray(json.loads((ROOT/'models/forecasting/phase3_demand_ar.json').read_text())['coefficients'])
    models={'persistence':None,'autoregressive':ar,'lstm':LSTMForecaster.load(ROOT/'models/forecasting/phase3_demand_lstm.json')};actual=[];pred={name:[] for name in models}
    for origin in report['test_origin_timestamps']:
        i=lookup[pd.Timestamp(origin)];history=frame.iloc[i-24:i];actual.extend(frame.demand_mw.iloc[i:i+24])
        for name,model in models.items():pred[name].extend(model.predict(history,24) if model else [float(history.demand_mw.iloc[-1])]*24)
    actual=np.asarray(actual);peak=float(actual.max());eligible=actual>=1.
    results={}
    for name,values in pred.items():
        values=np.asarray(values);metrics=forecast_metrics(actual,values)
        results[name]=dict(**metrics,mae_percent_test_peak=100*metrics['mae']/peak,rmse_percent_test_peak=100*metrics['rmse']/peak,
            mape_percent=float(np.mean(abs(actual[eligible]-values[eligible])/actual[eligible])*100),mape_excluded=int((~eligible).sum()))
    surrogate=json.loads((ROOT/'reports/phase3_surrogate.json').read_text());costs={name:np.asarray([e['outcomes'][name]['operating_cost'] for e in surrogate['paired_test_episodes']]) for name in ['baseline','q_learning','surrogate']}
    reductions={name:dict(mean_cost=float(costs[name].mean()),reduction_percent_of_mean_baseline=100*float((costs['baseline'].mean()-costs[name].mean())/costs['baseline'].mean())) for name in costs}
    result=dict(forecast=dict(geography='Delhi aggregate demand',cohort='46 held-out daily origins, 24 frozen hours each',samples=len(actual),test_peak_mw=peak,
        normalization='100 * MW error / maximum actual MW across the same evaluated test cohort',mape_policy='Exclude actual <1 MW; exclusion count reported; no solar/wind percentage claim',models=results),
        dispatch=dict(source='synthetic aggregate simulator',paired_episodes=14,costs=reductions,
        limitation='Simulator operating cost units and counterfactual dynamics are synthetic. Surrogate fidelity is not dispatch optimality or real cost savings.'))
    Path('reports/phase3_metrics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
