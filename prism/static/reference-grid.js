'use strict';
(() => {
  const root = document.getElementById('reference-grid');
  if (!root) return;
  const el = id => document.getElementById(id);
  const state = {data:null, assets:new Map(), connections:new Map(), selected:null, request:0, map:null, nodes:new Map(), lines:new Map(), locations:{}, locationSources:{}, telemetry:{snapshot:null,receivedAt:0,error:null,pending:false,nextFetch:0}};
  let labelFrame=0,filterTimer;
  const controls = ['ref-search','ref-kind','ref-boundary','ref-classification','ref-period','ref-connection-search'];
  const words = value => String(value ?? '').replaceAll('_',' ');
  const shown = value => value === null || value === undefined || value === '' ? 'Unknown' : String(value);
  const node = (tag, cls, text) => {const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
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
  const locationFor=id=>state.locations[id];
  function labelLayout(){if(!state.map||labelFrame)return;labelFrame=requestAnimationFrame(()=>{labelFrame=0;state.map.invalidateSize({pan:false});});}
  function zoom(factor){if(state.map)state.map.setZoom(state.map.getZoom()+(factor<1?1:-1));}
  function fit(includeExternal=true){
    if(!state.map)return;
    state.map.invalidateSize({pan:false});
    let assets=state.visibleAssets||state.data?.assets||[];
    if(!includeExternal){const internal=assets.filter(a=>a.boundary_classification==='internal');if(internal.length)assets=internal;}
    const points=assets.map(asset=>locationFor(asset.id)).filter(Boolean).map(p=>[p.latitude,p.longitude]);
    if(points.length)state.map.fitBounds(points,{padding:[45,45],maxZoom:13,animate:false});
    else state.map.setView([28.64,77.16],10,{animate:false});
  }
  function ensureMap(){
    if(state.map)return;
    if(!window.L)throw new Error('The local map library could not load. Reload this page to retry.');
    state.map=L.map('ref-network',{zoomControl:false,scrollWheelZoom:true,keyboard:true,minZoom:5,maxZoom:19,fadeAnimation:false,zoomAnimation:!matchMedia('(prefers-reduced-motion:reduce)').matches}).setView([28.64,77.16],10);
    let tileFailures=0;state.tiles=null;
    const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>',crossOrigin:true});
    tiles.on('tileerror',()=>{if(++tileFailures>=3){el('ref-map-error').textContent='Street-map tiles are unavailable. Geographic asset positions remain usable. Reload reference to retry.';el('ref-map-error').hidden=false;}});
    tiles.on('tileload',()=>{tileFailures=0;el('ref-map-error').hidden=true;});tiles.addTo(state.map);state.tiles=tiles;
    state.map.on('keydown',event=>{if(event.originalEvent.key==='Home'){event.originalEvent.preventDefault();fit();}});
  }
  function select(type,id,focusInspector=false) {
    if(!(type==='asset'?state.assets:state.connections).has(id))return;
    const previous=state.selected;state.selected={type,id};renderSelection();renderInspector();
    if(previous&&(previous.id!==id||previous.type!==type)&&!matchMedia('(prefers-reduced-motion:reduce)').matches){const panel=el('ref-detail');panel.getAnimations().forEach(animation=>animation.cancel());panel.animate([{opacity:.65},{opacity:1}],{duration:150,easing:'ease-out'});}
    const selected=type==='asset'?state.assets.get(id):null;
    if(selected)el('ref-status').textContent=`Selected ${selected.name} · source evidence and station loading.`;
    else el('ref-status').textContent=`Selected connection ${id} · dated source evidence.`;
    el('ref-evidence-jump').hidden=false;
    labelLayout();
    if(focusInspector){el('ref-inspector-title').setAttribute('tabindex','-1');el('ref-inspector-title').focus({preventScroll:true});}
  }
  function renderSelection() {
    root.querySelectorAll('[data-ref-asset]').forEach(n=>{const active=state.selected?.type==='asset'&&n.dataset.refAsset===state.selected.id;n.classList.toggle('selected',active);n.setAttribute('aria-pressed',String(active));});
    root.querySelectorAll('[data-ref-connection]').forEach(n=>{const active=state.selected?.type==='connection'&&n.dataset.refConnection===state.selected.id;n.classList.toggle('selected',active);if(n.tagName.toLowerCase()==='button')n.setAttribute('aria-pressed',String(active));});
    const selectedAsset=state.selected?.type==='asset'&&state.visibleAssets?.some(a=>a.id===state.selected.id)?state.selected.id:null;
    const selectedConnection=state.selected?.type==='connection'?state.visibleConnections?.find(c=>c.id===state.selected.id):null;
    const related=new Set(selectedAsset?[selectedAsset]:selectedConnection?[selectedConnection.source,selectedConnection.target]:[]);
    if(selectedAsset)(state.visibleConnections||[]).forEach(c=>{if(c.source===selectedAsset||c.target===selectedAsset){related.add(c.source);related.add(c.target);}});
    const active=Boolean(selectedAsset||selectedConnection);
    root.querySelectorAll('#ref-network .ref-node').forEach(n=>{n.classList.toggle('related',related.has(n.dataset.refAsset));n.classList.toggle('unrelated',active&&!related.has(n.dataset.refAsset));});
    root.querySelectorAll('#ref-network .ref-connection').forEach(n=>{const linked=selectedAsset?(n.dataset.source===selectedAsset||n.dataset.target===selectedAsset):n.dataset.refConnection===selectedConnection?.id;n.classList.toggle('related',Boolean(linked));n.classList.toggle('unrelated',active&&!linked);});
    if(state.map){
      const css=getComputedStyle(document.documentElement),accent=css.getPropertyValue('--teal').trim(),ink=css.getPropertyValue('--ink').trim(),muted=css.getPropertyValue('--muted').trim();
      state.lines.forEach((line,id)=>{const c=state.connections.get(id),linked=selectedAsset?(c.source===selectedAsset||c.target===selectedAsset):id===selectedConnection?.id;line.setStyle({color:linked?accent:muted,weight:linked?3:1.4,opacity:active?(linked ? .95 : .12):.45});});
      state.nodes.forEach((marker,id)=>{const chosen=state.selected?.type==='asset'&&state.selected.id===id,linked=related.has(id);marker.setStyle({color:chosen?accent:ink,weight:chosen?3:2,opacity:active && !linked ? .35 : 1,fillOpacity:active && !linked ? .35 : 1});marker.setRadius(chosen?8:state.assets.get(id)?.kind==='plant'?7:5);if(chosen){marker.bringToFront();marker.openTooltip();}else marker.closeTooltip();});
    }
    el('ref-asset-select').value=state.selected?.type==='asset'?state.selected.id:'';
    el('ref-connection-select').value=state.selected?.type==='connection'?state.selected.id:'';
  }
  function renderGraph(assets,connections){
    ensureMap();
    state.nodes.forEach(layer=>state.map.removeLayer(layer));state.lines.forEach(layer=>state.map.removeLayer(layer));state.nodes.clear();state.lines.clear();
    const colours=()=>{const css=getComputedStyle(document.documentElement);return {ink:css.getPropertyValue('--ink').trim(),accent:css.getPropertyValue('--teal').trim(),warning:css.getPropertyValue('--warning').trim(),muted:css.getPropertyValue('--muted').trim(),surface:css.getPropertyValue('--white').trim()};};
    const colour=colours();
    connections.forEach(c=>{
      const a=locationFor(c.source),b=locationFor(c.target);if(!a||!b)return;
      const line=L.polyline([[a.latitude,a.longitude],[b.latitude,b.longitude]],{color:colour.muted,weight:1.4,opacity:.45,dashArray:c.assertion_only?'3 5':period(c)==='2019'?'6 5':null});
      line.bindTooltip(node('span',null,connectionName(c)));line.on('click',()=>select('connection',c.id));line.addTo(state.map);state.lines.set(c.id,line);
      const element=line.getElement();if(element){element.dataset.refConnection=c.id;element.setAttribute('aria-label',connectionName(c)+', '+connectionCaption(c));}
    });
    assets.forEach(a=>{
      const point=locationFor(a.id);if(!point)return;
      const marker=L.circleMarker([point.latitude,point.longitude],{radius:a.kind==='plant'?7:5,color:planned(a)?colour.warning:colour.surface,weight:2,fillColor:a.kind==='plant'?colour.accent:colour.ink,fillOpacity:1,dashArray:planned(a)?'3 2':null});
      marker.bindTooltip(node('span',null,a.name),{direction:'top',className:'ref-map-label',offset:[0,-7]});marker.on('click',()=>select('asset',a.id));marker.addTo(state.map);state.nodes.set(a.id,marker);
      const element=marker.getElement();if(element){element.dataset.refAsset=a.id;element.setAttribute('tabindex','0');element.setAttribute('role','button');element.setAttribute('aria-label',a.name+', '+words(a.kind));element.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();select('asset',a.id);}});element.addEventListener('focus',()=>marker.openTooltip());element.addEventListener('blur',()=>{if(state.selected?.id!==a.id)marker.closeTooltip();});}
    });
    const count=state.nodes.size;
    el('ref-location-status').textContent=`${count} of ${assets.length} matching assets located. ${assets.length-count?assets.length-count+' awaiting a confirmed location; available in the directory.':''}`;
    el('ref-no-graph').hidden=assets.length>0;
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
    const {assets,connections}=filtered();
    const key=assets.map(a=>a.id).join('|')+'::'+connections.map(c=>c.id).join('|');
    if(key!==state.renderKey){state.renderKey=key;state.visibleAssets=assets;state.visibleConnections=connections;renderGraph(assets,connections);renderLedgers(assets,connections);renderSelection();fit(false);}
    el('ref-visible-count').textContent=`${state.nodes.size} located assets · ${state.lines.size} mapped connection records`;
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
      panel.append(node('span','ref-status-label',`${words(a.kind)} · ${planned(a)?'Planned at source date':'Source reference'}`),node('h4',null,a.name));
      const voltages=[...new Set([...(a.site_voltage_levels_kv||[]),a.corroborated_nominal_voltage_kv,...(a.voltage_assertions||[]).filter(v=>v.status!=='conflicted').flatMap(v=>v.levels_kv||[])].filter(v=>typeof v==='number'))].sort((x,y)=>y-x);
      const owners=[...new Set([a.reference_owner,...(a.ownership_assertions||[]).map(v=>v.owner)].filter(Boolean))];
      const aliases=[...new Set([...(a.aliases||[]).map(v=>typeof v==='string'?v:v.name),...(a.merged_inventory_ids||[])].filter(Boolean))];
      renderStationReading(panel,a);
      const metadata=node('details');metadata.append(node('summary',null,'Reference asset details'),node('p','ref-record-id',a.id));
      addFields(metadata,[['Boundary',words(a.boundary_classification)],['Source-reported voltage',voltages.length?`${voltages.join(' / ')} kV`:'Unknown'],['Source-reported ownership',owners.length?owners.join(' / '):'Unknown'],['Current operating state','Unknown'],['Measured output',a.current_output_mw==null?'Unknown':`${a.current_output_mw} MW`],['Available capacity',a.available_capacity_mw==null?'Unknown':`${a.available_capacity_mw} MW`],['Coordinates',locationFor(a.id)?`${locationFor(a.id).latitude.toFixed(5)}, ${locationFor(a.id).longitude.toFixed(5)} · WGS 84`:'Location not yet confirmed'],['Source aliases / merged IDs',aliases.length?aliases.join('; '):'None recorded'],['Reference grouping',a.reference_site_group||'None recorded']]);
      panel.append(metadata);
      const location=locationFor(a.id),locationSource=state.locationSources[location?.source_id];
      if(location&&locationSource){const locationNote=node('p','ref-location-source');locationNote.append(node('span',null,'Location source: '));const link=node('a',null,locationSource.title);link.href=locationSource.url;link.target='_blank';link.rel='noopener noreferrer';locationNote.append(link);if(location.precision)locationNote.append(node('span',null,' · '+location.precision));panel.append(locationNote);}

      if(planned(a))panel.append(node('p','ref-warning','Budella is classified as planned/under tendering in the June 2025 source. Named cable observations do not establish current commissioning.'));
      if(a.voltage_owner_note&&!a.voltage_owner_note.includes('Internal boundary classification follows the published Delhi address'))panel.append(node('p',null,a.voltage_owner_note));
      const issues=a.open_issue_ids||[];if(issues.length)panel.append(node('p','ref-warning',`Open source flags: ${issues.join(', ')}`));
      if(a.resolved_reference_issue_ids?.length)panel.append(node('p',null,`Reference decisions: ${a.resolved_reference_issue_ids.join(', ')}`));
      addSources(panel,a.evidence_ids);
      const associated=state.data.connections.filter(c=>c.source===a.id||c.target===a.id);
      const details=node('details');details.append(node('summary',null,`Connected evidence records (${associated.length})`));associated.forEach(c=>linkedButton(details,`${connectionName(c)} · ${connectionCaption(c)} · ${c.id}`,'connection',c.id));panel.append(details);
    } else {
      const c=state.connections.get(state.selected.id);if(!c)return;
      panel.append(node('span','ref-status-label',c.assertion_only?'Interface / section assertion':'Dated circuit observation'),node('h4',null,connectionName(c)));
      const identity=node('details');identity.append(node('summary',null,'Record identity'),node('p','ref-record-id',c.id));panel.append(identity);
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
    el('ref-telemetry-status').textContent=`${stale?'Stale station readings':'Published station readings'} · ${count} of ${snapshot.coverage?.reference_assets??state.data?.assets.length??'—'} assets mapped. Source times and quality: inspector.`;
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
    const request=++state.request;el('ref-retry').disabled=true;el('ref-error').hidden=true;el('ref-network').setAttribute('aria-busy','true');el('ref-status').textContent='Loading the saved Delhi reference inventory…';
    try {
      const response=await fetch('/api/reference-grid',{signal:AbortSignal.timeout(15000),cache:'no-cache'});const data=await response.json();
      if(!response.ok)throw new Error(data.message||'Reference inventory unavailable.');
      if(data.mode!=='reference_only'||!Array.isArray(data.assets)||!Array.isArray(data.connections)||!data.evidence)throw new Error('The reference response does not match the expected schema.');
      if(request!==state.request)return;
      const locationResponse=await fetch(el('ref-network').dataset.locationUrl,{signal:AbortSignal.timeout(15000),cache:'no-cache'});
      if(!locationResponse.ok)throw new Error('Geographic asset locations unavailable. Reload reference to retry.');
      const geography=await locationResponse.json();
      state.locations={};state.locationSources=geography.sources||{};
      for(const [id,point] of Object.entries(geography.locations||{})){if(Number.isFinite(point.latitude)&&Number.isFinite(point.longitude)&&point.latitude>=-90&&point.latitude<=90&&point.longitude>=-180&&point.longitude<=180&&/^https:\/\//.test(state.locationSources[point.source_id]?.url||''))state.locations[id]=point;}
      state.data=data;state.renderKey=null;if(state.tiles)state.tiles.redraw();state.assets=new Map(data.assets.map(a=>[a.id,a]));state.connections=new Map(data.connections.map(c=>[c.id,c]));
      el('ref-total-assets').textContent=data.assets.length;
      el('ref-total-circuits').textContent=data.connections.filter(c=>!c.assertion_only).length;
      el('ref-total-assertions').textContent=data.connections.filter(c=>c.assertion_only).length;
      el('ref-delhi-count').textContent=data.coverage?.source_referenced_delhi_asset_count??'Unknown';
      el('ref-content').hidden=false;fit();renderFiltered();
      if(state.selected && (state.selected.type==='asset'?state.assets:state.connections).has(state.selected.id))renderInspector();
      else {state.selected=null;const initial=data.assets.find(asset=>asset.id==='ss-bamnauli')||data.assets[0];if(initial)select('asset',initial.id);else renderInspector();}
      const questions=el('ref-field-questions');questions.replaceChildren();(data.coverage?.field_questions||[]).forEach(q=>questions.append(node('li',null,`${q.id}: ${q.reason}`)));
      el('ref-dataset').textContent=`Version: ${data.dataset}`;
      el('ref-status').textContent=`${data.assets.length} assets · ${data.connections.length} connection evidence records available.`;
    } catch(error) {
      if(request!==state.request)return;
      el('ref-content').hidden=true;el('ref-error').hidden=false;el('ref-error').textContent=error.name==='TimeoutError'?'The reference request timed out. Use Reload reference to retry.':`${error.message} Use Reload reference to retry.`;el('ref-status').textContent='Reference inventory unavailable. The separate synthetic workflows remain available.';
    } finally {if(request===state.request){el('ref-retry').disabled=false;el('ref-network').setAttribute('aria-busy','false');}}
  }
  controls.forEach(id=>{const search=id==='ref-search'||id==='ref-connection-search';el(id).addEventListener(search?'input':'change',()=>{clearTimeout(filterTimer);if(search)filterTimer=setTimeout(renderFiltered,100);else renderFiltered();});});
  const filterDisclosure=document.querySelector('.ref-advanced');
  document.addEventListener('pointerdown',event=>{if(filterDisclosure.open&&!filterDisclosure.contains(event.target))filterDisclosure.open=false;});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&filterDisclosure.open){filterDisclosure.open=false;filterDisclosure.querySelector('summary').focus();}});
  el('ref-asset-select').addEventListener('change',event=>{if(event.target.value)select('asset',event.target.value);});
  el('ref-connection-select').addEventListener('change',event=>{if(event.target.value)select('connection',event.target.value);});
  el('ref-reset').addEventListener('click',()=>{clearTimeout(filterTimer);controls.forEach(id=>{el(id).value=id==='ref-search'||id==='ref-connection-search'?'':'all';});state.selected=null;el('ref-evidence-jump').hidden=true;fit();renderFiltered();renderSelection();renderInspector();el('ref-status').textContent='Filters reset. All reference assets and evidence records are available.';});
  el('ref-evidence-jump').addEventListener('click',event=>{event.preventDefault();el('ref-inspector-title').focus();el('ref-inspector-title').scrollIntoView({block:'start'});});
  el('ref-retry').addEventListener('click',load);el('ref-fit').addEventListener('click',()=>fit(true));el('ref-zoom-in').addEventListener('click',()=>zoom(.8));el('ref-zoom-out').addEventListener('click',()=>zoom(1.25));
  load();
  loadStations();
  setInterval(loadStations,60000);
  setInterval(updateStationAge,15000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)loadStations();});
  const resizeObserver=new ResizeObserver(labelLayout);resizeObserver.observe(el('ref-network'));
  new MutationObserver(()=>renderSelection()).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  window.addEventListener('pagehide',event=>{if(!event.persisted){resizeObserver.disconnect();state.map?.remove();}});
  document.fonts.ready.then(labelLayout);
})();
