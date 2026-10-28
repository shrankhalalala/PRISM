"""Publish the reviewed refinement through the existing reversible validation gate."""
from hashlib import sha256
import json
from pathlib import Path
import pandas as pd
from prism.forecasting.evaluation import origins,evaluate
from prism.forecasting.models import forecast_metrics
from prism.forecasting.lifecycle import load_incumbent
from prism.forecasting.registry import REGISTRY,bootstrap,promote,verify_bundle
from prism.config import ROOT


def main():
    report=json.loads((ROOT/'reports/phase3_forecast_refinement.json').read_text())
    source=ROOT/'data/processed/delhi_demand_hourly.csv'
    if sha256(source.read_bytes()).hexdigest()!=report['hourly_sha256']:
        raise ValueError('Refinement data fingerprint changed')
    frame=pd.read_csv(source);a,b=int(len(frame)*.7),int(len(frame)*.85)
    indices=origins(frame,a,b)
    _,incumbent,old=load_incumbent()
    if pd.Timestamp(old['split']['training_end'])>=pd.Timestamp(frame.timestamp.iloc[indices[0]]):
        raise ValueError('Incumbent training overlaps candidate validation')
    actual,pred=evaluate(frame,indices,{'incumbent':incumbent})
    incumbent_rmse=forecast_metrics(actual,pred['incumbent'])['rmse']
    candidates=ROOT/'models/forecasting/refinement-2026-10-27'
    names={'autoregressive':report['autoregressive'],'lstm':report['lstm'],'persistence':'persistence'}
    selected=next(name for name,value in names.items() if value==report['selected'])
    expected=json.loads((candidates/'selection.json').read_text())
    if any(expected[key]!=report[key] for key in ('selected','autoregressive','lstm','hourly_sha256','validation')):
        raise ValueError('Selection record mismatch')
    # Validate artifact contents and reproduce the selected score before promotion.
    from prism.forecasting.direct import load_autoregressive
    from prism.forecasting import LSTMForecaster
    fitted={'autoregressive':load_autoregressive(candidates/'autoregressive.json'),'lstm':LSTMForecaster.load(candidates/'lstm.json'),'persistence':None}
    _,review=evaluate(frame,indices,fitted)
    metrics={name:{'validation':forecast_metrics(actual,review[name])} for name in fitted}
    for name,variant in names.items():
        if metrics[name]['validation']!=report['validation'][variant]:
            raise ValueError('Candidate score differs from reviewed evidence')
    bundle=dict(hourly_sha256=report['hourly_sha256'],base_hourly_sha256=report['hourly_sha256'],data_source='delhi_sldc',target='demand_mw',selected_on_validation=selected,model_variants=names,
                split={'training_end':report['training_end'],'validation_end':report['validation_end'],'test_end':report['test_end'],'method':'chronological_70_15_15'},validation_origins=len(indices),metrics=metrics,
                interval={**report['interval'],'method':'validation absolute-residual 90th percentile per horizon'},test_used_for_promotion=False,limitation=report['limitation'])
    bodies={name:(candidates/name).read_bytes() for name in ('lstm.json','autoregressive.json')}
    bodies['forecast_report.json']=(json.dumps(bundle,indent=2)+'\n').encode()
    hashes={name:sha256(raw).hexdigest() for name,raw in bodies.items()}
    version=sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    bootstrap();folder=REGISTRY/version
    if not folder.exists():
        folder.mkdir()
        for name,raw in bodies.items():(folder/name).write_bytes(raw)
        (folder/'manifest.json').write_text(json.dumps({'files':hashes},indent=2)+'\n')
    verify_bundle(version)
    result=promote(version,incumbent_rmse)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
