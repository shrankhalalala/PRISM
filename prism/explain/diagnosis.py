"""Topology/time-based investigation hypotheses, never verified physical causes."""
from datetime import datetime,timezone
from time import perf_counter
import networkx as nx
import numpy as np
from prism.config import ROOT
from prism.grid.model import load_grid
from prism.explain.reference_input import diagnostic_view


def graph_view(mode):
    graph=nx.Graph()
    if mode=='synthetic':
        data=load_grid(ROOT/'data/raw/grid.json')
        for node in data['nodes']:graph.add_node(node['id'])
        for edge in data['edges']:graph.add_edge(edge['source'],edge['target'],weight=1.,relation='CONNECTED_TO',evidence_ids=[edge['id']])
        return graph,'phase2_synthetic','Synthetic aggregate topology; no physical flow validation.'
    if mode!='reference':raise ValueError('dataset must be synthetic or reference')
    data=diagnostic_view()
    for asset in data['assets']:
        if not str(asset.get('reference_classification','')).startswith('planned'):graph.add_node(asset['id'])
    for edge in data['connections']:
        if edge['temporal_class']=='historical_2019_table':continue
        if edge['source'] in graph and edge['target'] in graph:
            graph.add_edge(edge['source'],edge['target'],weight=1.,relation='CONNECTED_TO',evidence_ids=edge['evidence_ids'])
    graph.graph['source_store']=data['source_store']
    return graph,data['dataset'],'Dated reference connectivity, excluding 2019-only records and planned assets; not current switching/flow state.'


def fixed_pagerank(graph,damping=.85,iterations=10):
    n=len(graph)
    if not n:return {},0.
    rank={node:1/n for node in graph};change=0
    for _ in range(iterations):
        dangling=sum(rank[node] for node in graph if graph.degree(node)==0)
        updated={node:(1-damping)/n+damping*dangling/n for node in graph}
        for node in graph:
            neighbors=list(graph.neighbors(node))
            for neighbor in neighbors:updated[neighbor]+=damping*rank[node]/len(neighbors)
        change=sum(abs(updated[node]-rank[node]) for node in graph);rank=updated
    return rank,change


def diagnose(body):
    start=perf_counter()
    if not isinstance(body,dict) or set(body)-{'dataset','alarms'}:raise ValueError('Provide dataset and alarms')
    graph,dataset,limitation=graph_view(body.get('dataset','reference'))
    alarms=body.get('alarms')
    if not isinstance(alarms,list) or not 1<=len(alarms)<=100:raise ValueError('Require 1..100 alarms')
    observed={}
    for alarm in alarms:
        if not isinstance(alarm,dict) or set(alarm)!={'asset_id','observed_at'}:raise ValueError('Alarm requires asset_id and observed_at only')
        if alarm['asset_id'] not in graph:raise ValueError('Alarm asset not eligible in selected graph')
        stamp=datetime.fromisoformat(alarm['observed_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None or (stamp-datetime.now(timezone.utc)).total_seconds()>120:raise ValueError('Require qualified, nonfuture alarm time')
        if alarm['asset_id'] not in observed or stamp<observed[alarm['asset_id']]:observed[alarm['asset_id']]=stamp
    earliest=min(observed.values());latest=max(observed.values());span=max(1,(latest-earliest).total_seconds())
    ranks,residual=fixed_pagerank(graph);candidates=set(observed)
    for asset in observed:candidates.update(nx.single_source_shortest_path_length(graph,asset,cutoff=2))
    results=[]
    for candidate in sorted(candidates):
        paths=[];proximity=0
        for asset in observed:
            if nx.has_path(graph,candidate,asset):
                path=nx.shortest_path(graph,candidate,asset);distance=len(path)-1;proximity+=1/(1+distance)
                paths.append(dict(alarm_asset=asset,path=path,connection_evidence=[graph[a][b]['evidence_ids'] for a,b in zip(path,path[1:])]))
        temporal=1-(observed[candidate]-earliest).total_seconds()/span if candidate in observed else 0
        timing_residual=None;fitted_lag=None
        if len(paths)>=2:
            distances=np.asarray([len(path['path'])-1 for path in paths],dtype=float)
            arrivals=np.asarray([(observed[path['alarm_asset']]-earliest).total_seconds() for path in paths])
            if np.ptp(distances)>0:
                slope=float(np.cov(distances,arrivals,bias=True)[0,1]/np.var(distances))
                fitted_lag=max(0.,slope)
                intercept=float(np.mean(arrivals-fitted_lag*distances))
                timing_residual=float(np.mean(np.abs(arrivals-(intercept+fitted_lag*distances))))
                temporal=1-min(1.,timing_residual/span)
            else:
                timing_residual=float(np.mean(np.abs(arrivals-arrivals.mean())))
                temporal=1-min(1.,timing_residual/span)
        score=.7*temporal+.2*proximity/len(observed)+.1*ranks[candidate]/max(ranks.values())
        results.append(dict(asset_id=candidate,heuristic_score=score,has_observed_alarm=candidate in observed,
            first_observed_at=observed[candidate].isoformat() if candidate in observed else None,
            pagerank=ranks[candidate],paths=paths,timing_residual_seconds=timing_residual,fitted_seconds_per_hop=fitted_lag))
    results.sort(key=lambda row:(-row['heuristic_score'],row['asset_id']))
    return dict(dataset=dataset,source_store=graph.graph.get('source_store','synthetic_fixture'),hypotheses=results[:10],alarms_received=len(alarms),
        method='BFS connectivity + nonnegative linear hop-time consistency + fixed-iteration PageRank',damping=.85,iterations=10,
        pagerank_l1_change=residual,pagerank_converged=residual<1e-6,
        relationship_semantics='Undirected CONNECTED_TO, constant structural weight 1 in [0,1]; no SUPPLIES_TO/SERVES direction without evidence.',
        elapsed_ms=(perf_counter()-start)*1000,verified_cause=False,executable=False,
        limitation=limitation+' Hypotheses prioritize investigation; no causal probability or electrical propagation proof. Equal hop delays are a heuristic assumption and timestamps may reflect reporting delays. Alarm correlation can reflect a common external cause.')
