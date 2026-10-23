"""Cold/warm uncached TreeSHAP timing and labeled graph-investigation fixtures."""
import json
from pathlib import Path
from time import perf_counter
from datetime import datetime,timedelta,timezone
import numpy as np
import networkx as nx
from prism.explain.attribution import BACKGROUND,explain
from prism.explain.diagnosis import diagnose,graph_view
from prism.simulation import Observation,Action
from prism.dispatch.q_learning import ACTION_ORDER


def main():
    background=json.loads(BACKGROUND.read_text());latency=[];residuals=[];disagreements=0
    for row in background['rows']:
        obs=Observation(*row[:5],bool(row[5]));valid=tuple(a for i,a in enumerate(ACTION_ORDER) if int(row[9])&(1<<i))
        start=perf_counter();result=explain(obs,valid);latency.append((perf_counter()-start)*1000);residuals.append(abs(result['additivity_residual']));disagreements+=not result['agreement']
    graph,_,_=graph_view('synthetic');cases=[]
    # Procedural graph fixtures, not simulated physical fault ground truth.
    for source in graph:
        distances=nx.single_source_shortest_path_length(graph,source)
        alarms=[]
        for node,distance in distances.items():
            if node!=source and distance<=2:
                alarms.append(dict(asset_id=node,observed_at=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=distance*5)).isoformat()))
        if not alarms:continue
        result=diagnose(dict(dataset='synthetic',alarms=alarms))
        ordered=[r['asset_id'] for r in result['hypotheses']]
        cases.append(dict(hidden_fixture_source=source,source_not_passed_to_engine=True,top1=ordered[0]==source,top3=source in ordered[:3],elapsed_ms=result['elapsed_ms']))
    report=dict(attribution=dict(samples=100,background_samples=100,response_cache=False,cold_ms=latency[0],
        warm_uncached_ms={'p50':float(np.percentile(latency[1:],50)),'p95':float(np.percentile(latency[1:],95)),'max':max(latency[1:])},
        max_additivity_residual=max(residuals),policy_disagreements=disagreements,
        scope='actual surrogate prediction + 100-background interventional TreeSHAP + formatting; first call includes lazy model/explainer initialization'),
        diagnosis=dict(cases=cases,top1_rate=sum(c['top1'] for c in cases)/len(cases),top3_rate=sum(c['top3'] for c in cases)/len(cases),
        fixture='Synthetic graph-distance alarm fixtures with hidden source excluded from input. No physical propagation or real failure ground truth.',causal_accuracy_established=False))
    Path('reports/phase3_explanations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['attribution']));print('Graph fixture top3:',report['diagnosis']['top3_rate'])

if __name__=='__main__':main()
