/* Paced backend connectivity snapshots. This view never computes electrical flows. */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  if(!$('topo-form'))return;
  const ns='http://www.w3.org/2000/svg';
  const state={source:null,running:false,loading:false,controller:null,stopped:false,received:0,total:24,last:null};
  const svgNode=(tag,attrs,text)=>{const el=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));if(text!==undefined)el.textContent=text;return el;};
  const textNode=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
  const num=value=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('en-IN'):'—';
  const stamp=value=>{const date=new Date(value);return value&&Number.isFinite(date.valueOf())?date.toLocaleString('en-IN',{timeZone:'Asia/Kolkata',hour12:false})+' IST':'Unknown emission time';};
  const error=message=>{$('topo-error').hidden=!message;$('topo-error').textContent=message||'';};
  const assetName=id=>state.source?.assets?.find(asset=>asset.id===id)?.name||id;
  function limits(){
    const steps=Math.max(1,Math.min(96,Number($('topo-steps').value)||1));
    $('topo-fault-step').max=String(steps-1);$('topo-fault-duration').max=String(steps);
    if(Number($('topo-fault-step').value)>=steps)$('topo-fault-step').value=String(steps-1);
    if(Number($('topo-fault-duration').value)>steps)$('topo-fault-duration').value=String(steps);
    const fault=Boolean($('topo-fault-asset').value);
    $('topo-fault-step').disabled=state.running||!fault;$('topo-fault-duration').disabled=state.running||!fault;
  }
  function lock(running){
    state.running=running;
    Array.from($('topo-form').elements).forEach(control=>control.disabled=running);
    $('topo-run').disabled=running||!state.source;$('topo-run').setAttribute('aria-busy',String(running));
    $('topo-stop').disabled=!running;$('topo-source-retry').disabled=running||state.loading;limits();
  }
  function highlightTarget(){
    const chosen=$('topo-fault-asset').value;
    $('topo-network').querySelectorAll('[data-topo-id]').forEach(el=>el.classList.toggle('chosen',el.dataset.topoId===chosen));
  }
  function draw(source){
    state.source=source;const svg=$('topo-network');svg.replaceChildren(svgNode('title',{id:'topo-graph-title'},'Delhi reference connectivity scenario'));
    const positions=new Map(source.assets.map((asset,i)=>{const angle=i/Math.max(1,source.assets.length)*Math.PI*2;return [asset.id,asset.layout&&Number.isFinite(asset.layout.x)&&Number.isFinite(asset.layout.y)?asset.layout:{x:500+400*Math.cos(angle),y:350+280*Math.sin(angle)}];}));
    const points=[...positions.values()];
    if(points.length){const minX=Math.min(...points.map(p=>p.x)),maxX=Math.max(...points.map(p=>p.x)),minY=Math.min(...points.map(p=>p.y)),maxY=Math.max(...points.map(p=>p.y));svg.setAttribute('viewBox',`${minX-45} ${minY-45} ${Math.max(160,maxX-minX+150)} ${Math.max(160,maxY-minY+100)}`);}
    const pairs=new Map();source.connections.forEach(connection=>{const key=[connection.source,connection.target].sort().join('|');if(!pairs.has(key))pairs.set(key,[]);pairs.get(key).push(connection);});
    const lines=svgNode('g',{});
    for(const group of pairs.values())group.forEach((connection,i)=>{const a=positions.get(connection.source),b=positions.get(connection.target);if(!a||!b)return;const dx=b.x-a.x,dy=b.y-a.y,length=Math.hypot(dx,dy)||1,offset=(i-(group.length-1)/2)*7;const path=svgNode('path',{d:`M${a.x} ${a.y} Q${(a.x+b.x)/2-dy/length*offset} ${(a.y+b.y)/2+dx/length*offset} ${b.x} ${b.y}`,class:'topo-edge','data-topo-id':connection.id});path.append(svgNode('title',{},`${assetName(connection.source)} ↔ ${assetName(connection.target)} · ${connection.id}`));lines.append(path);});svg.append(lines);
    const nodes=svgNode('g',{});source.assets.forEach(asset=>{const point=positions.get(asset.id),g=svgNode('g',{transform:`translate(${point.x},${point.y})`,class:'topo-node','data-topo-id':asset.id});g.append(svgNode('circle',{r:8}),svgNode('title',{},`${asset.name} · ${asset.id}`),svgNode('text',{x:12,y:4},asset.name));nodes.append(g);});svg.append(nodes);highlightTarget();
  }
  async function loadReference(){
    if(state.loading||state.running)return;state.loading=true;$('topo-source-retry').disabled=true;error('');$('topo-source-status').textContent='Loading Delhi reference choices…';
    try{const response=await fetch('/api/reference-grid',{signal:AbortSignal.timeout(15000),headers:{Accept:'application/json'}});const data=await response.json();if(!response.ok||!Array.isArray(data.assets)||!Array.isArray(data.connections))throw new Error('Reference inventory unavailable.');
      draw(data);const select=$('topo-fault-asset'),previous=select.value;select.replaceChildren();const none=textNode('option','No injected outage');none.value='';select.append(none);
      const assets=document.createElement('optgroup');assets.label='Delhi reference assets';data.assets.forEach(asset=>{const option=textNode('option',asset.name);option.value=asset.id;assets.append(option);});select.append(assets);
      const connections=document.createElement('optgroup');connections.label='Dated connection evidence';data.connections.forEach(connection=>{const option=textNode('option',`${assetName(connection.source)} ↔ ${assetName(connection.target)} · ${connection.id}`);option.value=connection.id;connections.append(option);});select.append(connections);
      if(Array.from(select.options).some(option=>option.value===previous))select.value=previous;
      $('topo-source-status').textContent=`${data.assets.length} reference assets · ${data.connections.length} connection records available. Eligibility and conducting assumptions are qualified by the scenario backend.`;
      $('topo-caption').textContent='Reference preview. All displayed positions are schematic; run a scenario for backend-computed connectivity states.';
    }catch(err){error(err.name==='TimeoutError'?'Reference request timed out. Reload reference to retry.':err.message);$('topo-source-status').textContent='Reference choices unavailable. Reload to retry.';}finally{state.loading=false;lock(false);highlightTarget();}
  }
  function eventLog(text){const list=$('topo-log');if(!state.received&&list.children.length===1&&list.firstElementChild.textContent==='No scenario steps received.')list.replaceChildren();list.append(textNode('li',text));}
  function consume(event){
    if(event.type==='error')throw new Error(event.message||event.error||'Scenario backend reported an error.');
    if(event.type==='start'){
      if(!Array.isArray(event.assets)||!Array.isArray(event.connections))throw new Error('Invalid scenario start snapshot.');
      draw(event);state.received=0;state.last=null;$('topo-log').replaceChildren();
      $('topo-assurance').textContent=typeof event.assurance==='string'?event.assurance:JSON.stringify(event.assurance||{});
      $('topo-components').textContent=num(event.baseline?.component_count);$('topo-isolated').textContent='—';$('topo-connections').textContent='—';
      $('topo-status').textContent='Backend connectivity scenario started. Waiting for the first computed step.';return;
    }
    if(event.type==='step'){
      state.received++;state.last=event;$('topo-progress').value=state.received;
      const failedAssets=new Set(event.failed_asset_ids||[]),failedConnections=new Set(event.failed_connection_ids||[]),blocked=new Set(event.blocked_connection_ids||[]),activeAssets=new Set(event.active_asset_ids||[]),activeConnections=new Set(event.active_connection_ids||[]);
      $('topo-network').querySelectorAll('.topo-node').forEach(node=>{const id=node.dataset.topoId;node.classList.toggle('failed',failedAssets.has(id));node.classList.toggle('inactive',!activeAssets.has(id)&&!failedAssets.has(id));});
      $('topo-network').querySelectorAll('.topo-edge').forEach(edge=>{const id=edge.dataset.topoId;edge.classList.toggle('failed',failedConnections.has(id));edge.classList.toggle('blocked',blocked.has(id));edge.classList.toggle('inactive',!activeConnections.has(id)&&!failedConnections.has(id)&&!blocked.has(id));});
      $('topo-components').textContent=num(event.component_count);$('topo-isolated').textContent=Array.isArray(event.isolated_asset_ids)?num(event.isolated_asset_ids.length):'—';$('topo-connections').textContent=Array.isArray(event.active_connection_ids)?`${num(event.active_connection_ids.length)} / ${state.source.connections.length}`:'—';
      $('topo-status').textContent=`Received step ${event.step} · ${state.received} / ${event.total_steps} snapshots · ${event.simulated_minutes} modeled minutes.`;
      $('topo-caption').textContent=`Backend emission ${stamp(event.emitted_at)}. Colors show reference-model availability, injected outages and blocked connectivity, not electrical flow.`;
      const events=(event.events||[]).map(item=>`${assetName(item.asset_id)}: ${item.event}`).join('; ');
      eventLog(`Step ${event.step} · ${num(event.component_count)} components · ${Array.isArray(event.isolated_asset_ids)?event.isolated_asset_ids.length:'unknown'} isolated assets · ${Array.isArray(event.newly_isolated_asset_ids)?event.newly_isolated_asset_ids.length:'unknown'} newly isolated beyond baseline${events?' · '+events:''}`);return;
    }
    if(event.type==='complete'){if(event.status!=='completed')throw new Error('The scenario ended without a completed status.');$('topo-status').textContent=`Connectivity scenario completed · ${state.received} backend snapshots received.`;state.completed=true;}
  }
  $('topo-form').addEventListener('submit',async event=>{
    event.preventDefault();if(state.running||!state.source)return;limits();error('');state.stopped=false;state.completed=false;state.received=0;state.total=Number($('topo-steps').value);state.controller=new AbortController();
    const target=$('topo-fault-asset').value,body={steps:state.total,interval_ms:Number($('topo-interval').value),faults:target?[{asset_id:target,step:Number($('topo-fault-step').value),duration_steps:Number($('topo-fault-duration').value)}]:[]};
    $('topo-progress').max=state.total;$('topo-progress').value=0;lock(true);$('topo-status').textContent='Connecting to the backend scenario stream…';let reader;
    try{const headers={'Content-Type':'application/json',Accept:'application/x-ndjson'};const token=$('ops-token')?.value.trim();if(token)headers['X-PRISM-Operator-Token']=token;
      const response=await fetch('/api/topology-scenario/stream',{method:'POST',headers,body:JSON.stringify(body),signal:state.controller.signal});
      if(!response.ok){const failure=await response.json().catch(()=>({}));throw new Error(failure.message||failure.error||`Scenario request failed (${response.status}).`);}if(!response.body)throw new Error('Streaming is unavailable in this browser.');
      reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';
      while(true){const chunk=await reader.read();if(chunk.done)break;buffer+=decoder.decode(chunk.value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines)if(line.trim())consume(JSON.parse(line));}
      buffer+=decoder.decode();if(buffer.trim())consume(JSON.parse(buffer));if(!state.completed)throw new Error('The backend stream ended before completion. Last received state is retained.');
    }catch(err){if(state.stopped||err.name==='AbortError')$('topo-status').textContent=`Scenario stopped · ${state.received} snapshots received. Last computed state is retained.`;else{error(err.message||'Scenario stream failed. Retry to start a new run.');$('topo-status').textContent='Scenario unavailable or interrupted. Last received state, if any, is retained.';}}
    finally{state.controller.abort();if(reader)await reader.cancel().catch(()=>{});state.controller=null;lock(false);}
  });
  $('topo-stop').addEventListener('click',()=>{if(!state.running)return;state.stopped=true;state.controller?.abort();});
  $('topo-steps').addEventListener('input',limits);$('topo-fault-asset').addEventListener('change',()=>{limits();highlightTarget();});$('topo-source-retry').addEventListener('click',loadReference);
  window.addEventListener('pagehide',()=>state.controller?.abort());
  loadReference();
})();
