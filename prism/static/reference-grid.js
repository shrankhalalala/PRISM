'use strict';
(() => {
  const root = document.getElementById('reference-grid');
  if (!root) return;
  const el = id => document.getElementById(id);
  const ns = 'http://www.w3.org/2000/svg';
  const state = {data:null, assets:new Map(), connections:new Map(), selected:null, request:0, view:{x:-60,y:-50,w:1120,h:800}, drag:null, telemetry:{snapshot:null,receivedAt:0,error:null,pending:false,nextFetch:0}};
  const controls = ['ref-search','ref-kind','ref-boundary','ref-classification','ref-period','ref-connection-search'];
  const words = value => String(value ?? '').replaceAll('_',' ');
  const shown = value => value === null || value === undefined || value === '' ? 'Unknown' : String(value);
  const node = (tag, cls, text) => {const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  const svgNode = (tag, attrs, text) => {const n=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([key,value])=>n.setAttribute(key,value));if(text!==undefined)n.textContent=text;return n;};
  const planned = asset => String(asset.reference_classification || '').startsWith('planned');
  const name = id => state.assets.get(id)?.name || id;
  const connectionName = c => `${name(c.source)} ↔ ${name(c.target)}`;
  const connectionCaption = c => `${c.voltage_kv ? `${c.voltage_kv} kV · ` : ''}${c.circuit_label ? `Ckt ${c.circuit_label} · ` : ''}${c.source_id || 'Reviewed interface'} · ${c.source_date || words(c.temporal_class || c.kind)}`;
  const assetText = a => [a.id,a.name,...(a.aliases||[]).map(v=>typeof v==='string'?v:v.name),...(a.merged_inventory_ids||[])].join(' ').toLowerCase();
  const period = c => c.temporal_class === 'historical_2019_table' ? '2019' : c.temporal_class === 'later_dtl_table' ? 'dtl' : 'other';
  const filters = () => ({search:el('ref-search').value.trim().toLowerCase(),kind:el('ref-kind').value,boundary:el('ref-boundary').value,classification:el('ref-classification').value,period:el('ref-period').value,connectionSearch:el('ref-connection-search').value.trim().toLowerCase()});
  function filtered() {
    const f=filters();
    const assets=state.data.assets.filter(a=>(!f.search||assetText(a).includes(f.search))&&(f.kind==='all'||a.kind===f.kind)&&(f.boundary==='all'||a.boundary_classification===f.boundary)&&(f.classification==='all'||(f.classification==='planned'?planned(a):!planned(a))));
    const ids=new Set(assets.map(a=>a.id));
    const connections=state.data.connections.filter(c=>ids.has(c.source)&&ids.has(c.target)&&(f.period==='all'||period(c)===f.period)&&(!f.connectionSearch||[connectionName(c),connectionCaption(c),c.id,c.detail].join(' ').toLowerCase().includes(f.connectionSearch)));
    return {assets,connections};
  }
  function position(asset,index) {
    if(asset.layout && Number.isFinite(asset.layout.x) && Number.isFinite(asset.layout.y))return asset.layout;
    const angle=2*Math.PI*index/Math.max(1,state.data.assets.length);
    return {x:500+400*Math.cos(angle),y:350+280*Math.sin(angle)};
  }
  function view() {const v=state.view;el('ref-network').setAttribute('viewBox',`${v.x} ${v.y} ${v.w} ${v.h}`);labelLayout();}
  function zoom(factor) {
    const v=state.view;const w=Math.max(180,Math.min(2500,v.w*factor));const h=w*800/1120;
    state.view={x:v.x+(v.w-w)/2,y:v.y+(v.h-h)/2,w,h};view();
  }
  function fit() {state.view={x:-60,y:-50,w:1120,h:800};view();}
  function select(type,id,focusInspector=false) {
    if(!(type==='asset'?state.assets:state.connections).has(id))return;
    state.selected={type,id};renderSelection();renderInspector();
    const selected=type==='asset'?state.assets.get(id):null;
    if(selected)el('ref-status').textContent=`Inspecting ${selected.name}. Source-reported metadata with separate published station loading below.`;
    else el('ref-status').textContent=`Inspecting connection record ${id}. Dated source evidence; no operating flow is inferred.`;
    el('ref-evidence-jump').hidden=false;
    labelLayout();
    if(focusInspector){el('ref-inspector-title').setAttribute('tabindex','-1');el('ref-inspector-title').focus({preventScroll:true});}
  }
  function renderSelection() {
    root.querySelectorAll('[data-ref-asset]').forEach(n=>{const active=state.selected?.type==='asset'&&n.dataset.refAsset===state.selected.id;n.classList.toggle('selected',active);n.setAttribute('aria-pressed',String(active));});
    root.querySelectorAll('[data-ref-connection]').forEach(n=>{const active=state.selected?.type==='connection'&&n.dataset.refConnection===state.selected.id;n.classList.toggle('selected',active);if(n.tagName.toLowerCase()==='button')n.setAttribute('aria-pressed',String(active));});
    el('ref-asset-select').value=state.selected?.type==='asset'?state.selected.id:'';
    el('ref-connection-select').value=state.selected?.type==='connection'?state.selected.id:'';
  }
  function renderGraph(assets,connections) {
    const svg=el('ref-network');svg.replaceChildren();
    const positions=new Map(state.data.assets.map((a,i)=>[a.id,position(a,i)]));
    const lineLayer=svgNode('g',{'aria-label':'Dated reference connections'});
    const pairs=new Map();
    connections.forEach(c=>{const key=[c.source,c.target].sort().join('|');if(!pairs.has(key))pairs.set(key,[]);pairs.get(key).push(c);});
    for(const group of pairs.values())group.forEach((c,index)=>{
      const a=positions.get(c.source),b=positions.get(c.target);if(!a||!b)return;
      const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;
      const offset=(index-(group.length-1)/2)*9;
      const mx=(a.x+b.x)/2-dy/len*offset,my=(a.y+b.y)/2+dx/len*offset;
      const classes=['ref-connection'];if(period(c)==='2019')classes.push('ref-historical');if(c.assertion_only)classes.push('ref-assertion');if(c.kind==='historical_isolated_line')classes.push('ref-isolated');
      const path=svgNode('path',{d:`M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`,class:classes.join(' '),'data-ref-connection':c.id,'aria-label':`${connectionName(c)}, ${connectionCaption(c)}`});
      path.append(svgNode('title',{},`${connectionName(c)} · ${c.id}`));
      path.addEventListener('click',()=>select('connection',c.id));lineLayer.append(path);
    });
    svg.append(lineLayer);
    const layer=svgNode('g',{'aria-label':'Reference assets'});
    assets.forEach(a=>{
      const p=positions.get(a.id),classes=['ref-node'];if(a.kind==='plant')classes.push('ref-plant');if(planned(a))classes.push('ref-planned');if(a.boundary_classification==='external_boundary')classes.push('ref-external');
      const g=svgNode('g',{transform:`translate(${p.x},${p.y})`,class:classes.join(' '),tabindex:'0',role:'button','data-ref-asset':a.id,'aria-pressed':'false','aria-label':`${a.name}, ${words(a.kind)}${planned(a)?', planned at source date':''}`});
      const shape=a.kind==='plant'?svgNode('rect',{x:-8,y:-8,width:16,height:16,class:'ref-node-shape'}):svgNode('circle',{r:7,class:'ref-node-shape'});
      g.append(shape,svgNode('text',{x:11,y:4,class:'ref-node-label'},a.name.replace(/ \([^)]*\)/g,'').replace('Power Station','PS')));
      g.append(svgNode('title',{},`${a.name} · ${a.id}`));
      g.addEventListener('pointerenter',labelLayout);g.addEventListener('pointerleave',labelLayout);g.addEventListener('focus',labelLayout);g.addEventListener('blur',labelLayout);g.addEventListener('click',()=>select('asset',a.id));g.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select('asset',a.id);}});layer.append(g);
    });svg.append(layer);view();el('ref-no-graph').hidden=assets.length>0;
  }
  function labelLayout() {
    if(!state.data)return;
    const svg=el('ref-network'),rect=svg.getBoundingClientRect();
    if(!rect.width||!rect.height)return;
    const scale=Math.min(rect.width/state.view.w,rect.height/state.view.h);
    const selected=state.selected?.type==='asset'?state.selected.id:null;
    const groups=[...svg.querySelectorAll('.ref-node')];
    const boxes=[];
    groups.sort((a,b)=>Number(b.dataset.refAsset===selected)-Number(a.dataset.refAsset===selected));
    for(const g of groups){
      const text=g.querySelector('text');if(!text)continue;
      const active=g.dataset.refAsset===selected||g.matches(':hover')||g===document.activeElement;
      const readable=rect.width>=600||active||state.view.w<500;
      const fontSize=(active?12:10)/Math.max(scale,.08);
      text.style.fontSize=`${fontSize}px`;
      text.setAttribute('x',String(11/Math.max(scale,.2)));
      text.style.display=readable?'':'none';
      if(!readable)continue;
      const box=text.getBoundingClientRect();
      const overlaps=boxes.some(b=>box.left<b.right+5&&box.right+5>b.left&&box.top<b.bottom+3&&box.bottom+3>b.top);
      if(!active&&overlaps){text.style.display='none';continue;}
      boxes.push(box);
    }
  }
  function option(value,text) {const o=node('option',null,text);o.value=value;return o;}
  function recordButton(type,id,title,caption) {
    const button=node('button','ref-record-button');button.type='button';button.dataset[type==='asset'?'refAsset':'refConnection']=id;button.setAttribute('aria-pressed','false');button.append(node('strong',null,title),node('small',null,caption));button.addEventListener('click',()=>select(type,id));return button;
  }
  function renderLedgers(assets,connections) {
    const selectAssets=el('ref-asset-select'),selectConnections=el('ref-connection-select');
    selectAssets.replaceChildren(option('','Choose an asset…'));selectConnections.replaceChildren(option('','Choose a connection record…'));
    const listAssets=el('ref-asset-list'),listConnections=el('ref-connection-list');listAssets.replaceChildren();listConnections.replaceChildren();
    assets.forEach(a=>{selectAssets.append(option(a.id,a.name));listAssets.append(recordButton('asset',a.id,a.name,`${words(a.kind)} · ${planned(a)?'Planned at source date':words(a.boundary_classification)}`));});
    connections.forEach(c=>{selectConnections.append(option(c.id,`${connectionName(c)} · ${connectionCaption(c)} · ${c.id}`));listConnections.append(recordButton('connection',c.id,connectionName(c),`${connectionCaption(c)} · ${c.id}`));});
    if(!assets.length)listAssets.append(node('p','ref-empty','No matching assets. Try a different name or reset filters.'));
    if(!connections.length)listConnections.append(node('p','ref-empty','No matching connection records. Both endpoints must match the asset filters.'));
    selectAssets.disabled=!assets.length;selectConnections.disabled=!connections.length;
    el('ref-asset-count').textContent=`${assets.length} / ${state.data.assets.length}`;
    el('ref-connection-count').textContent=`${connections.length} / ${state.data.connections.length}`;
  }
  function renderFiltered() {
    if(!state.data)return;
    const {assets,connections}=filtered();renderGraph(assets,connections);renderLedgers(assets,connections);renderSelection();
    el('ref-visible-count').textContent=`${assets.length} / ${state.data.assets.length} assets · ${connections.length} / ${state.data.connections.length} records`;
  }
  function addFields(parent,fields) {const dl=node('dl');fields.forEach(([title,value])=>{const row=node('div');row.append(node('dt',null,title),node('dd',null,shown(value)));dl.append(row);});parent.append(dl);}
  function addSources(parent,ids) {
    const unique=[...new Set(ids||[])];const details=node('details');details.append(node('summary',null,`Source evidence (${unique.length})`));const list=node('ul');
    unique.forEach(id=>{
      const evidence=state.data.evidence[id];const li=node('li');
      if(!evidence){li.textContent=`${id} · source details unavailable`;list.append(li);return;}
      const label=`${evidence.source_id||id} · ${evidence.source_date||'Source date unspecified'}`;
      try {const url=new URL(evidence.url||evidence.source_url);if(url.protocol!=='https:')throw new Error('Unsafe evidence URL');const a=node('a',null,label);a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';li.append(a);}catch{li.append(node('span',null,label));}
      li.append(node('span','ref-evidence-locator',`Locator: ${JSON.stringify(evidence.locator||{})}`));
      if(evidence.source_sha256)li.append(node('span','ref-evidence-locator',`SHA-256: ${evidence.source_sha256}`));
      list.append(li);
    });if(!unique.length)list.append(node('li',null,'No source IDs supplied.'));details.append(list);parent.append(details);
  }
  function linkedButton(parent,text,type,id) {const b=node('button','ref-linked-button',text);b.type='button';b.addEventListener('click',()=>select(type,id));parent.append(b);}
  function renderInspector() {
    const panel=el('ref-detail');panel.replaceChildren();
    if(!state.selected){panel.append(node('p','ref-empty','Select an asset or connection to inspect its identity and source evidence.'));return;}
    if(state.selected.type==='asset') {
      const a=state.assets.get(state.selected.id);if(!a)return;
      panel.append(node('span','ref-status-label',`${words(a.kind)} · ${planned(a)?'Planned at source date':'Source reference'}`),node('h4',null,a.name),node('p','ref-record-id',a.id));
      const voltages=[...new Set([...(a.site_voltage_levels_kv||[]),a.corroborated_nominal_voltage_kv,...(a.voltage_assertions||[]).filter(v=>v.status!=='conflicted').flatMap(v=>v.levels_kv||[])].filter(v=>typeof v==='number'))].sort((x,y)=>y-x);
      const owners=[...new Set([a.reference_owner,...(a.ownership_assertions||[]).map(v=>v.owner)].filter(Boolean))];
      const aliases=[...new Set([...(a.aliases||[]).map(v=>typeof v==='string'?v:v.name),...(a.merged_inventory_ids||[])].filter(Boolean))];
      addFields(panel,[['Boundary',words(a.boundary_classification)],['Source-reported voltage',voltages.length?`${voltages.join(' / ')} kV`:'Unknown'],['Source-reported ownership',owners.length?owners.join(' / '):'Unknown'],['Current operating state','Unknown'],['Measured output',a.current_output_mw==null?'Unknown':`${a.current_output_mw} MW`],['Available capacity',a.available_capacity_mw==null?'Unknown':`${a.available_capacity_mw} MW`],['Coordinates','Unknown · schematic positions only'],['Source aliases / merged IDs',aliases.length?aliases.join('; '):'None recorded'],['Reference grouping',a.reference_site_group||'None recorded']]);
      renderStationReading(panel,a);
      if(planned(a))panel.append(node('p','ref-warning','Budella is classified as planned/under tendering in the June 2025 source. Named cable observations do not establish current commissioning.'));
      if(a.voltage_owner_note)panel.append(node('p',null,a.voltage_owner_note));
      const issues=a.open_issue_ids||[];if(issues.length)panel.append(node('p','ref-warning',`Open source flags: ${issues.join(', ')}`));
      if(a.resolved_reference_issue_ids?.length)panel.append(node('p',null,`Reference decisions: ${a.resolved_reference_issue_ids.join(', ')}`));
      addSources(panel,a.evidence_ids);
      const associated=state.data.connections.filter(c=>c.source===a.id||c.target===a.id);
      const details=node('details');details.append(node('summary',null,`Connected evidence records (${associated.length})`));associated.forEach(c=>linkedButton(details,`${connectionName(c)} · ${connectionCaption(c)} · ${c.id}`,'connection',c.id));panel.append(details);
      if(a.notes?.length){const notes=node('details');notes.append(node('summary',null,'Original inventory notes'));a.notes.forEach(text=>notes.append(node('p',null,text)));panel.append(notes);}
    } else {
      const c=state.connections.get(state.selected.id);if(!c)return;
      panel.append(node('span','ref-status-label',c.assertion_only?'Interface / section assertion':'Dated circuit observation'),node('h4',null,connectionName(c)),node('p','ref-record-id',c.id));
      addFields(panel,[['Record type',words(c.kind)],['Source-reported voltage',c.voltage_kv==null?'Unknown':`${c.voltage_kv} kV`],['Circuit suffix',c.circuit_label||'Unknown / not assigned'],['Source',c.source_id||'Reviewed sources below'],['Source date',c.source_date||'Unspecified; see evidence'],['Evidence period',words(c.temporal_class||'Source-qualified assertion')],['Current operating state','Unknown'],['Measured flow','Unknown'],['Thermal limit','Unknown']]);
      if(c.detail)panel.append(node('p',null,c.detail));
      if(c.kind==='historical_isolated_line')panel.append(node('p','ref-warning','Historically isolated / zero-load evidence. This record must not be treated as a conducting power path.'));
      if(c.assertion_only)panel.append(node('p',null,'An interface assertion is not automatically an extra physical transmission circuit.'));
      if(c.issue_ids?.length)panel.append(node('p','ref-warning',`Open source flags: ${c.issue_ids.join(', ')}`));
      linkedButton(panel,`Inspect ${name(c.source)}`,'asset',c.source);linkedButton(panel,`Inspect ${name(c.target)}`,'asset',c.target);addSources(panel,c.evidence_ids);
    }
  }
  const measurement = value => typeof value==='number'&&Number.isFinite(value) ? value.toLocaleString('en-IN',{maximumFractionDigits:3}) : 'Unknown';
  function stationAge(reading) {
    return typeof reading.age_seconds==='number' ? Math.max(0,reading.age_seconds+(Date.now()-state.telemetry.receivedAt)/1000) : null;
  }
  function readingState(reading) {
    return state.telemetry.error||reading.status!=='live'||stationAge(reading)>300 ? 'stale' : 'live';
  }
  function stationSummary() {
    const telemetry=state.telemetry,snapshot=telemetry.snapshot;
    if(!snapshot){el('ref-telemetry-status').textContent=telemetry.error?'Station loading unavailable · no valid station reading received. Checks once per minute.':'Station loading · connecting to the published SLDC station feed…';return;}
    const readings=snapshot.readings||[];
    const stale=telemetry.error||readings.some(r=>readingState(r)==='stale');
    const count=snapshot.coverage?.measured_assets??new Set(readings.map(r=>r.asset_id)).size;
    el('ref-telemetry-status').textContent=`${stale?'Stale published':'Published'} station loading · ${count} / ${snapshot.coverage?.reference_assets??state.data?.assets.length??'—'} reference assets have source readings. Inspect an asset for source time and quality flags. Checks once per minute.`;
  }
  function renderStationReading(parent,asset) {
    const section=node('section','ref-station-reading');section.setAttribute('aria-label','Published SLDC station loading');
    section.append(node('h5',null,'Published station loading'));
    const telemetry=state.telemetry;
    const readings=(telemetry.snapshot?.readings||[]).filter(r=>r.asset_id===asset.id&&r.measurement_role==='station_loading');
    if(!readings.length){
      section.append(node('p','ref-station-empty',telemetry.snapshot?'Unknown · no eligible published station reading is mapped to this asset.':telemetry.error?'Unknown · station source unavailable.':'Checking published station readings…'));
      section.append(node('p','ref-station-note','No station value is inferred from Delhi-wide demand, a nearby asset or a reference rating.'));
    }else readings.forEach(reading=>{
      const status=readingState(reading),badge=node('span',`ref-station-freshness ${status}`,status==='live'?'Fresh source reading':'Stale source reading');
      section.append(badge,node('p','ref-source-label',`SLDC label: ${shown(reading.source_label)}`));
      const values=node('div','ref-station-values');
      for(const [label,value,unit] of [['Station loading',reading.mw,'MW'],['Reactive power',reading.mvar,'MVAr'],['Measured voltage',reading.voltage_kv,'kV']]){
        const item=node('div');item.append(node('span',null,label),node('strong',null,measurement(value)),node('small',null,unit));values.append(item);
      }
      section.append(values);
      let time='Unknown';
      const date=new Date(reading.observed_at);if(reading.observed_at&&Number.isFinite(date.getTime()))time=`${date.toLocaleString('en-IN',{timeZone:'Asia/Kolkata',hour12:false})} IST`;
      const age=stationAge(reading);
      section.append(node('p','ref-station-time',`Source time: ${time}${age===null?'':` · age ${Math.floor(age)}s`}`));
      section.append(node('p','ref-station-note',`Source status (uninterpreted): ${shown(reading.source_status_raw)}`));
      if(reading.quality_flags?.length)section.append(node('p','ref-station-note',`Quality flags: ${reading.quality_flags.map(words).join('; ')}.`));
    });
    section.append(node('p','ref-station-note','Station MW is loading, not generator output, available capacity or a line thermal limit. The sign convention and RTU status are unverified.'));
    parent.append(section);
  }
  function updateStationAge() {
    stationSummary();
    if(state.selected?.type==='asset'&&state.data){
      const previous=el('ref-detail').querySelector('.ref-station-reading');
      if(previous){const holder=node('div');renderStationReading(holder,state.assets.get(state.selected.id));previous.replaceWith(holder.firstElementChild);}
    }
  }
  async function loadStations() {
    const telemetry=state.telemetry;
    if(telemetry.pending||document.hidden||Date.now()<telemetry.nextFetch)return;
    telemetry.pending=true;telemetry.nextFetch=Date.now()+60000;
    try {
      const response=await fetch('/api/live/stations',{signal:AbortSignal.timeout(15000),cache:'no-store'});
      const data=await response.json();
      if(!['live','stale','unavailable'].includes(data.status)||!Array.isArray(data.readings)||(!response.ok&&response.status!==503))throw new Error('Invalid station response');
      if(data.status==='unavailable'||!data.readings.length){telemetry.error=data.error||'Station source unavailable.';}
      else{telemetry.snapshot=data;telemetry.receivedAt=Date.now();telemetry.error=null;}
    }catch{telemetry.error='Station source unavailable or returned an invalid response.';}
    finally{telemetry.pending=false;updateStationAge();}
  }
  async function load() {
    const request=++state.request;el('ref-retry').disabled=true;el('ref-error').hidden=true;el('ref-status').textContent='Loading the saved Delhi reference inventory…';
    try {
      const response=await fetch('/api/reference-grid',{signal:AbortSignal.timeout(15000),cache:'no-cache'});const data=await response.json();
      if(!response.ok)throw new Error(data.message||'Reference inventory unavailable.');
      if(data.mode!=='reference_only'||!Array.isArray(data.assets)||!Array.isArray(data.connections)||!data.evidence)throw new Error('The reference response does not match the expected schema.');
      if(request!==state.request)return;
      state.data=data;state.assets=new Map(data.assets.map(a=>[a.id,a]));state.connections=new Map(data.connections.map(c=>[c.id,c]));
      el('ref-total-assets').textContent=data.assets.length;
      el('ref-total-circuits').textContent=data.connections.filter(c=>!c.assertion_only).length;
      el('ref-total-assertions').textContent=data.connections.filter(c=>c.assertion_only).length;
      el('ref-delhi-count').textContent=data.coverage?.source_referenced_delhi_asset_count??'Unknown';
      el('ref-content').hidden=false;fit();renderFiltered();
      if(state.selected && (state.selected.type==='asset'?state.assets:state.connections).has(state.selected.id))renderInspector();
      else {state.selected=null;renderInspector();}
      const questions=el('ref-field-questions');questions.replaceChildren();(data.coverage?.field_questions||[]).forEach(q=>questions.append(node('li',null,`${q.id}: ${q.reason}`)));
      el('ref-dataset').textContent=`Version: ${data.dataset}`;
      el('ref-status').textContent=`Reference inventory ready · ${data.assets.length} assets and ${data.connections.length} individually inspectable evidence records. Mapped live station loading is shown separately in the inspector.`;
    } catch(error) {
      if(request!==state.request)return;
      el('ref-content').hidden=true;el('ref-error').hidden=false;el('ref-error').textContent=error.name==='TimeoutError'?'The reference request timed out. Use Reload reference to retry.':`${error.message} Use Reload reference to retry.`;el('ref-status').textContent='Reference inventory unavailable. The separate synthetic workflows remain available.';
    } finally {if(request===state.request)el('ref-retry').disabled=false;}
  }
  controls.forEach(id=>el(id).addEventListener(id==='ref-search'||id==='ref-connection-search'?'input':'change',renderFiltered));
  el('ref-asset-select').addEventListener('change',event=>{if(event.target.value)select('asset',event.target.value);});
  el('ref-connection-select').addEventListener('change',event=>{if(event.target.value)select('connection',event.target.value);});
  el('ref-reset').addEventListener('click',()=>{controls.forEach(id=>{el(id).value=id==='ref-search'||id==='ref-connection-search'?'':'all';});state.selected=null;el('ref-evidence-jump').hidden=true;fit();renderFiltered();renderInspector();el('ref-status').textContent='Filters reset. All reference assets and evidence records are available.';});
  el('ref-evidence-jump').addEventListener('click',event=>{event.preventDefault();el('ref-inspector-title').focus();el('ref-inspector-title').scrollIntoView({block:'start'});});
  el('ref-retry').addEventListener('click',load);el('ref-fit').addEventListener('click',fit);el('ref-zoom-in').addEventListener('click',()=>zoom(.8));el('ref-zoom-out').addEventListener('click',()=>zoom(1.25));
  const svg=el('ref-network');
  svg.addEventListener('keydown',event=>{
    if(event.key==='+'||event.key==='='){event.preventDefault();zoom(.8);}else if(event.key==='-'){event.preventDefault();zoom(1.25);}else if(event.key==='Home'){event.preventDefault();fit();}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();const amount=state.view.w*.06;state.view.x+=event.key==='ArrowLeft'?-amount:event.key==='ArrowRight'?amount:0;state.view.y+=event.key==='ArrowUp'?-amount:event.key==='ArrowDown'?amount:0;view();}
  });
  svg.addEventListener('wheel',event=>{if(event.ctrlKey){event.preventDefault();zoom(event.deltaY<0?.9:1.1);}},{passive:false});
  svg.addEventListener('pointerdown',event=>{if(event.button!==0||event.target.closest('.ref-node,.ref-connection'))return;state.drag={id:event.pointerId,x:event.clientX,y:event.clientY,view:{...state.view}};svg.setPointerCapture(event.pointerId);svg.classList.add('is-panning');});
  svg.addEventListener('pointermove',event=>{if(!state.drag||state.drag.id!==event.pointerId)return;const rect=svg.getBoundingClientRect();state.view.x=state.drag.view.x-(event.clientX-state.drag.x)*state.view.w/rect.width;state.view.y=state.drag.view.y-(event.clientY-state.drag.y)*state.view.h/rect.height;view();});
  const endPan=()=>{state.drag=null;svg.classList.remove('is-panning');};svg.addEventListener('pointerup',endPan);svg.addEventListener('pointercancel',endPan);svg.addEventListener('lostpointercapture',endPan);
  load();
  loadStations();
  setInterval(loadStations,60000);
  setInterval(updateStationAge,15000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)loadStations();});
  new ResizeObserver(labelLayout).observe(svg);
})();
