'use strict';
const $ = id => document.getElementById(id);
const number = value => Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-IN', {maximumFractionDigits: 1}) : '—';
let grid = null;
let selectedId = null;
let activeKind = 'all';
let activeSeries = 'demand_mw';
let activeHours = 24;
let measurementData = null;
let measurementRequest = 0;
const seriesNames = {demand_mw:'Demand',solar_mw:'Solar',wind_mw:'Wind'};
const preferences = {get(key){try{return localStorage.getItem(key);}catch{return null;}},set(key,value){try{localStorage.setItem(key,value);}catch{}}};
const mobileQuery=matchMedia('(max-width:800px)');
let desktopCollapsed=preferences.get('prism-sidebar-collapsed')==='true';
let drawerOpen=false;
function updateSidebar(){
  const visible=mobileQuery.matches?drawerOpen:!desktopCollapsed;
  document.body.classList.toggle('sidebar-collapsed',!mobileQuery.matches&&desktopCollapsed);
  document.body.classList.toggle('drawer-open',mobileQuery.matches&&drawerOpen);
  $('sidebar').inert=!visible;
  $('sidebar').setAttribute('aria-hidden',String(!visible));
  $('sidebar-toggle').setAttribute('aria-expanded',String(visible));
  $('sidebar-toggle').setAttribute('aria-label',visible?'Collapse navigation':'Open navigation');
  $('sidebar-backdrop').hidden=!(mobileQuery.matches&&drawerOpen);
}
function updateActiveNavigation(){
  const requested=location.hash.slice(1);
  const section=document.getElementById(requested)?requested:'overview';
  document.querySelectorAll('#sidebar nav a').forEach(link=>{
    const active=link.getAttribute('href')===`#${section}`;
    link.classList.toggle('active',active);
    if(active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');
  });
  const current=document.querySelector(`#sidebar nav a[href="#${section}"]`);
  $('breadcrumb-section').textContent=current?.dataset.navLabel||'Grid overview';
}
function closeDrawer(){drawerOpen=false;updateSidebar();$('sidebar-toggle').focus();}
$('sidebar-toggle').addEventListener('click',()=>{if(mobileQuery.matches){drawerOpen=!drawerOpen;}else{desktopCollapsed=!desktopCollapsed;preferences.set('prism-sidebar-collapsed',String(desktopCollapsed));}updateSidebar();});
$('sidebar-backdrop').addEventListener('click',closeDrawer);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&drawerOpen)closeDrawer();});
$('sidebar').querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{if(mobileQuery.matches)closeDrawer();}));
mobileQuery.addEventListener('change',()=>{drawerOpen=false;updateSidebar();});
updateSidebar();
if(!location.hash)history.replaceState(null,'','#overview');
window.addEventListener('hashchange',updateActiveNavigation);
updateActiveNavigation();
const darkQuery=matchMedia('(prefers-color-scheme:dark)');
let explicitTheme=preferences.get('prism-theme');
function setTheme(theme){document.documentElement.dataset.theme=theme;const dark=theme==='dark';$('theme-icon').textContent=dark?'☀':'☾';$('theme-label').textContent=dark?'Light':'Dark';$('theme-toggle').setAttribute('aria-label',`Switch to ${dark?'light':'dark'} theme`);}
setTheme(explicitTheme==='dark'||explicitTheme==='light'?explicitTheme:darkQuery.matches?'dark':'light');
$('theme-toggle').addEventListener('click',()=>{explicitTheme=document.documentElement.dataset.theme==='dark'?'light':'dark';preferences.set('prism-theme',explicitTheme);setTheme(explicitTheme);});
darkQuery.addEventListener('change',()=>{if(!explicitTheme)setTheme(darkQuery.matches?'dark':'light');});
const svgNS = 'http://www.w3.org/2000/svg';
function svgElement(tag, attributes = {}, content) {
  const el = document.createElementNS(svgNS, tag);
  Object.entries(attributes).forEach(([key,value]) => el.setAttribute(key,value));
  if (content !== undefined) el.textContent = content;
  return el;
}
function element(tag, className, content) {
  const el = document.createElement(tag);
  if(className) el.className = className;
  if(content !== undefined) el.textContent = content;
  return el;
}
function selectNode(id) {
  selectedId = id;
  $('asset-select').value = id;
  const node = grid.nodes.find(n => n.id === id);
  if (!node) return;
  document.querySelectorAll('#network .node').forEach(el => {
    const selected = el.dataset.id === id;
    el.classList.toggle('selected', selected);
    el.setAttribute('aria-pressed', String(selected));
  });
  const detail = $('node-detail');
  detail.replaceChildren(element('span', 'asset-kind', node.kind.replaceAll('_',' ')), element('h3', '', node.name));
  const fields = [['Asset ID', node.id], ['Status', node.status]];
  if(node.fuel) fields.push(['Source',node.fuel]);
  if(node.capacity_mw !== undefined) fields.push(['Capacity',`${number(node.capacity_mw)} MW`]);
  if(node.output_mw !== undefined) fields.push(['Output',`${number(node.output_mw)} MW`]);
  if(node.demand_mw !== undefined) fields.push(['Demand',`${number(node.demand_mw)} MW`]);
  const dl = element('dl');
  fields.forEach(([label,value]) => { const row=element('div');row.append(element('dt','',label),element('dd','',value));dl.append(row); });
  detail.append(dl);
  applyNetworkFocus();
}
function renderGrid(data) {
  grid = data;
  ['generation','demand','balance'].forEach(key => $(key).textContent = number(data.summary[`${key}_mw`]));
  $('nodes').textContent = number(data.summary.nodes);
  $('edges').textContent = `${number(data.summary.edges)} transmission connections`;
  const picker = $('asset-select'); picker.replaceChildren(); picker.disabled = !data.nodes.length;
  data.nodes.forEach(node => { const option=element('option','',`${node.name} · ${node.kind}`);option.value=node.id;picker.append(option); });
  populateFaultAssets(data);
  const svg = $('network'); svg.replaceChildren();
  if(!data.nodes.length) { svg.append(svgElement('text',{x:380,y:185,'text-anchor':'middle'},'No network nodes available.')); $('node-detail').replaceChildren(element('p','empty','No assets available.'));return; }
  const xs = data.nodes.map(n => Number(n.x)), ys = data.nodes.map(n => Number(n.y));
  const minX=Math.min(...xs), maxX=Math.max(...xs), minY=Math.min(...ys), maxY=Math.max(...ys);
  const positions = new Map(data.nodes.map(n => [n.id,{x:95+(Number(n.x)-minX)/(maxX-minX||1)*570,y:55+(Number(n.y)-minY)/(maxY-minY||1)*225}]));
  data.edges.forEach(edge => {
    const a=positions.get(edge.source), b=positions.get(edge.target);
    if(!a||!b)return;
    const line=svgElement('path',{d:`M ${a.x} ${a.y} L ${b.x} ${b.y}`,class:'connection'});
    line.dataset.source=edge.source;line.dataset.target=edge.target;
    line.append(svgElement('title',{},`${edge.id}: ${number(edge.capacity_mw)} MW capacity; ${edge.status}`));svg.append(line);
  });
  const colors={plant:'#246f68',substation:'#182d39',load:'#cf531f'};
  data.nodes.forEach(node => {
    const {x,y}=positions.get(node.id);
    const group=svgElement('g',{class:'node',tabindex:'0',role:'button','aria-label':`Inspect ${node.name}, ${node.kind}`,'aria-pressed':'false',transform:`translate(${x},${y})`});group.dataset.id=node.id;group.dataset.kind=node.kind;
    group.append(svgElement('circle',{r:23,fill:'#fafbf6',stroke:'#d4ddd0','stroke-width':1,class:'node-shape'}));
    group.append(svgElement(node.kind==='substation'?'rect':'circle',node.kind==='substation'?{x:-7,y:-7,width:14,height:14,fill:colors[node.kind]}:{r:8,fill:colors[node.kind]||colors.plant}));
    const name=svgElement('text',{y:39,'text-anchor':'middle'},node.name);group.append(name);
    const value=node.kind==='plant'?`${number(node.output_mw)} MW output`:node.kind==='load'?`${number(node.demand_mw)} MW demand`:'Substation';
    group.append(svgElement('text',{y:54,'text-anchor':'middle',class:'node-sub'},value));
    group.addEventListener('click',()=>selectNode(node.id));
    group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectNode(node.id);}});
    svg.append(group);
  });
  selectNode(data.nodes.some(n=>n.id===selectedId)?selectedId:data.nodes[0].id);
}
function applyNetworkFocus(){
  document.querySelectorAll('#network .node').forEach(node=>node.classList.toggle('dimmed',activeKind!=='all'&&node.dataset.kind!==activeKind));
  document.querySelectorAll('#network .connection').forEach(line=>line.classList.toggle('connected',line.dataset.source===selectedId||line.dataset.target===selectedId));
}
document.querySelectorAll('button[data-kind]').forEach(button=>button.addEventListener('click',()=>{
  activeKind=button.dataset.kind;
  document.querySelectorAll('button[data-kind]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
  const match=grid?.nodes.find(node=>activeKind==='all'||node.kind===activeKind);
  if(match)selectNode(match.id);else applyNetworkFocus();
}));
function renderMeasurements(data) {
  measurementData=data;
  $('record-count').textContent=`${data.records.length} HOURLY RECORDS`;
  const body=$('measurement-rows');body.replaceChildren();
  if(!data.records.length) {const row=element('tr');const cell=element('td','','No measurements available.');cell.colSpan=6;row.append(cell);body.append(row);}
  data.records.forEach(record=>{
    const row=element('tr');
    const timestamp=String(record.timestamp).replace('T',' ').replace('+00:00','').replace('Z','');
    [timestamp,number(record.demand_mw),number(record.solar_mw),number(record.wind_mw),Number(record.frequency_hz).toFixed(2),record.quality_flag].forEach((value,index)=>row.append(element('td',index===5?'quality':'',value)));
    body.append(row);
  });
  renderChart();
}
function renderChart(){
  const svg=$('measurement-chart');svg.dataset.series=activeSeries;svg.replaceChildren();
  const records=measurementData?.records||[];
  if(!records.length){$('chart-caption').textContent='No measurement observations are available for this range.';return;}
  const max=Math.max(1,...records.map(row=>Number(row[activeSeries])))*1.08;
  const x=index=>65+index/Math.max(1,records.length-1)*810;
  const y=value=>175-Number(value)/max*145;
  for(let i=0;i<4;i++){
    const value=max*i/3,py=y(value);
    svg.append(svgElement('line',{x1:65,x2:875,y1:py,y2:py,class:'chart-grid'}),svgElement('text',{x:52,y:py+4,'text-anchor':'end',class:'chart-axis'},number(value)));
  }
  svg.append(svgElement('text',{x:20,y:16,class:'chart-axis'},'MW'));
  const coords=records.map((row,index)=>`${x(index)},${y(row[activeSeries])}`).join(' ');
  svg.append(svgElement('polygon',{points:`65,175 ${coords} 875,175`,class:'chart-area'}));
  svg.append(svgElement('polyline',{points:coords,class:'chart-line','data-series':activeSeries}));
  const formatUTC=timestamp=>new Date(timestamp).toLocaleString('en-GB',{timeZone:'UTC',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false});
  [...new Set([0,Math.floor((records.length-1)/2),records.length-1])].forEach(index=>svg.append(svgElement('text',{x:x(index),y:204,'text-anchor':index===0?'start':index===records.length-1?'end':'middle',class:'chart-axis'},formatUTC(records[index].timestamp))));
  records.forEach((row,index)=>{const point=svgElement('circle',{cx:x(index),cy:y(row[activeSeries]),r:3,class:'chart-point'});point.append(svgElement('title',{},`${formatUTC(row.timestamp)} UTC: ${number(row[activeSeries])} MW`));svg.append(point);});
  $('chart-caption').textContent=`${seriesNames[activeSeries]} · ${records.length} synthetic hourly observations · ${formatUTC(records[0].timestamp)} to ${formatUTC(records.at(-1).timestamp)} UTC · Peak ${number(Math.max(...records.map(row=>Number(row[activeSeries]))))} MW. Full values are available in the measurement table below.`;
}
async function loadMeasurements(){
  const request=++measurementRequest;
  $('chart-status').textContent=`Loading ${activeHours===24?'24-hour':'7-day'} sample…`;
  $('measurement-chart').setAttribute('aria-busy','true');
  document.querySelectorAll('button[data-hours]').forEach(button=>button.disabled=true);
  try{
    const data=await getJSON(`/api/measurements?limit=${activeHours}`);
    if(request!==measurementRequest)return;
    renderMeasurements(data);
    document.querySelectorAll('button[data-hours]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.hours)===activeHours)));
    $('chart-status').textContent='Sample loaded · Select a series to explore · No live feed';
  }catch(error){if(request===measurementRequest)$('chart-status').textContent='Measurements could not be loaded. Previous chart, if present, is unchanged. Use Refresh data to retry.';throw error;
  }finally{if(request===measurementRequest){document.querySelectorAll('button[data-hours]').forEach(button=>button.disabled=false);$('measurement-chart').setAttribute('aria-busy','false');}}
}
document.querySelectorAll('button[data-series]').forEach(button=>button.addEventListener('click',()=>{activeSeries=button.dataset.series;document.querySelectorAll('button[data-series]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));renderChart();}));
document.querySelectorAll('button[data-hours]').forEach(button=>button.addEventListener('click',()=>{activeHours=Number(button.dataset.hours);loadMeasurements().catch(()=>{});}));
async function getJSON(path) {
  const response=await fetch(path,{headers:{Accept:'application/json'},signal:AbortSignal.timeout(10000)});
  const payload=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(payload.message||`${path} returned ${response.status}`);
  return payload;
}
async function postJSON(path,body){
  const response=await fetch(path,{method:'POST',headers:{Accept:'application/json','Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
  const payload=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(payload.message||`${path} returned ${response.status}`);
  return payload;
}
async function refresh() {
  $('refresh').disabled=true;$('error').hidden=true;$('load-status').textContent='Loading workspace data…';
  const resources=[['/api/grid'],['/api/measurements']];
  const results=await Promise.allSettled([getJSON('/api/grid').then(renderGrid),loadMeasurements()]);
  const failures=results.flatMap((result,index)=>result.status==='rejected'?[resources[index][0]]:[]);
  if(failures.length){
    $('error').textContent=`Could not load ${failures.join(', ')}. Check that the Flask service is running and try Refresh data. Any previously loaded values may be out of date.`;$('error').hidden=false;$('load-status').textContent='Workspace partially unavailable · Refresh to retry';
  }else{$('load-status').textContent=`Sample data loaded · ${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})} local time · No live feed`;}
  $('refresh').disabled=false;
}
$('asset-select').addEventListener('change',event=>selectNode(event.target.value));
$('refresh').addEventListener('click',refresh);
refresh();

const precise=(value,digits=2)=>Number.isFinite(Number(value))?Number(value).toLocaleString('en-IN',{maximumFractionDigits:digits}):'—';
const modelNames={persistence:'Persistence',autoregressive:'Autoregressive',lstm:'LSTM'};
function lineChart(svg,series,{xLabels=[],unit='MW',caption=''}={}){
  svg.replaceChildren();
  const title=svgElement('title',{},caption||'Line chart');
  const desc=svgElement('desc',{},`${series.map(item=>item.name).join(' and ')} across ${series[0]?.values.length||0} points, measured in ${unit}.`);
  svg.append(title,desc);
  const values=series.flatMap(item=>item.values).map(Number).filter(Number.isFinite);
  if(!values.length){svg.append(svgElement('text',{x:450,y:130,'text-anchor':'middle',class:'chart-axis'},'No trajectory values available.'));return;}
  let min=Math.min(...values),max=Math.max(...values);
  if(min===max){min=Math.max(0,min-1);max+=1;}
  const margin=(max-min)*.08;
  min=Math.max(0,min-margin);max+=margin;
  const count=Math.max(...series.map(item=>item.values.length));
  const x=index=>65+index/Math.max(1,count-1)*810;
  const y=value=>205-(Number(value)-min)/(max-min)*165;
  for(let index=0;index<4;index++){
    const value=min+(max-min)*index/3,py=y(value);
    svg.append(svgElement('line',{x1:65,x2:875,y1:py,y2:py,class:'chart-grid'}),svgElement('text',{x:52,y:py+4,'text-anchor':'end',class:'chart-axis'},precise(value,1)));
  }
  svg.append(svgElement('text',{x:18,y:18,class:'chart-axis'},unit));
  series.forEach((item,seriesIndex)=>{
    const coords=item.values.map((value,index)=>`${x(index)},${y(value)}`).join(' ');
    if(series.length===1)svg.append(svgElement('polygon',{points:`65,205 ${coords} 875,205`,class:'chart-area lab-area'}));
    const line=svgElement('polyline',{points:coords,class:`chart-line lab-line series-${seriesIndex}`,'data-series-name':item.name});
    line.append(svgElement('title',{},item.name));svg.append(line);
    item.values.forEach((value,index)=>{const point=svgElement('circle',{cx:x(index),cy:y(value),r:3,class:`chart-point lab-point series-${seriesIndex}`});point.append(svgElement('title',{},`${item.name}, ${xLabels[index]||`point ${index+1}`}: ${precise(value)} ${unit}`));svg.append(point);});
  });
  [...new Set([0,Math.floor((count-1)/2),count-1])].forEach(index=>svg.append(svgElement('text',{x:x(index),y:238,'text-anchor':index===0?'start':index===count-1?'end':'middle',class:'chart-axis'},xLabels[index]||String(index+1))));
}

function renderForecast(data){
  const predictions=Array.isArray(data.predictions)?data.predictions.map(Number):[];
  if(!predictions.length||predictions.some(value=>!Number.isFinite(value)))throw new Error('The forecast service returned no usable predictions.');
  const target=data.target||$('forecast-target').value;
  const model=data.model||$('forecast-model').value;
  const targetName=seriesNames[target]||target;
  $('forecast-result-label').textContent=`${predictions.length}-HOUR OUTLOOK`;
  $('forecast-result-model').textContent=(modelNames[model]||model).toUpperCase();
  const list=$('forecast-values');list.replaceChildren();
  predictions.forEach((value,index)=>{const item=element('li');item.append(element('span','',`T + ${String(index+1).padStart(2,'0')} h`),element('strong','',precise(value)));list.append(item);});
  lineChart($('forecast-chart'),[{name:targetName,values:predictions}],{xLabels:predictions.map((_,index)=>`T+${index+1}h`),unit:'MW',caption:`${targetName} forecast from the ${modelNames[model]||model} model`});
  const peak=Math.max(...predictions),low=Math.min(...predictions);
  $('forecast-caption').textContent=`${targetName} · ${modelNames[model]||model} · ${predictions.length} synthetic forecast values · Range ${precise(low)}–${precise(peak)} MW.`;
  $('forecast-results').hidden=false;
}

$('forecast-form').addEventListener('submit',async event=>{
  event.preventDefault();
  const button=$('forecast-run');button.disabled=true;$('forecast-error').hidden=true;$('forecast-results').hidden=true;
  $('forecast-status').textContent='Running forecast against synthetic history…';
  try{
    const query=new URLSearchParams({target:$('forecast-target').value,model:$('forecast-model').value,horizon:$('forecast-horizon').value});
    const data=await getJSON(`/api/forecast?${query}`);renderForecast(data);
    $('forecast-status').textContent=`Forecast ready · ${data.horizon_hours||data.predictions.length} hour horizon · Synthetic data`;
  }catch(error){$('forecast-error').textContent=`Forecast failed: ${error.message}`;$('forecast-error').hidden=false;$('forecast-status').textContent='Forecast unavailable. Adjust the controls or retry.';
  }finally{button.disabled=false;}
});

function populateFaultAssets(data){
  const select=$('fault-asset');
  const previous=select.value;
  select.replaceChildren();
  const none=element('option','','No injected fault');none.value='';select.append(none);
  const nodes=(data.nodes||[]).map(item=>({id:item.id,label:`${item.name} · ${item.kind}`}));
  const edges=(data.edges||[]).map(item=>({id:item.id,label:`${item.id} · transmission line`}));
  [...nodes,...edges].forEach(asset=>{const option=element('option','',asset.label);option.value=asset.id;select.append(option);});
  select.disabled=false;
  if([...select.options].some(option=>option.value===previous))select.value=previous;
  updateFaultControls();
}
function updateFaultControls(){
  const enabled=Boolean($('fault-asset').value);
  $('fault-step').disabled=!enabled;$('fault-duration').disabled=!enabled;
}
function syncScenarioLimits(){
  const steps=Math.max(1,Math.min(96,Number($('scenario-steps').value)||1));
  $('fault-step').max=String(steps-1);
  $('fault-duration').max=String(steps);
  if(Number($('fault-step').value)>=steps)$('fault-step').value=String(Math.max(0,steps-1));
  if(Number($('fault-duration').value)>steps)$('fault-duration').value=String(steps);
}
$('fault-asset').addEventListener('change',updateFaultControls);
$('scenario-steps').addEventListener('input',syncScenarioLimits);
syncScenarioLimits();

function trajectoryObservation(row){return row.observation||row.state||row.next_observation||{};}
function trajectoryBalance(row){
  const observation=trajectoryObservation(row);
  return Number(observation.generation_mw||0)-Number(observation.demand_mw||0);
}
function renderScenario(data){
  const totals=data.totals||{};
  $('scenario-return').textContent=precise(totals.return,3);
  $('scenario-unserved').textContent=precise(totals.unserved_mwh,3);
  $('scenario-curtailed').textContent=precise(totals.curtailed_mwh,3);
  $('scenario-cost').textContent=precise(totals.operating_cost,1);
  $('scenario-emissions').textContent=precise(totals.emissions_kg,1);
  const trajectory=Array.isArray(data.trajectory)?data.trajectory:[];
  const demand=trajectory.map(row=>Number(trajectoryObservation(row).demand_mw||0));
  const generation=trajectory.map(row=>Number(trajectoryObservation(row).generation_mw||0));
  lineChart($('scenario-chart'),[{name:'Demand',values:demand},{name:'Generation',values:generation}],{xLabels:trajectory.map((_,index)=>`Step ${index}`),unit:'MW',caption:'Demand and generation during the simulated episode'});
  const selectedPolicy=data.policy||$('scenario-policy').value;
  $('scenario-caption').textContent=`${trajectory.length} synthetic 15-minute steps · ${String(selectedPolicy).replaceAll('_',' ')} · Demand and generation in MW.`;
  const body=$('event-rows');body.replaceChildren();
  trajectory.forEach((row,index)=>{
    const tr=element('tr');
    const faults=Array.isArray(row.active_faults)&&row.active_faults.length?`Fault: ${row.active_faults.join(', ')}`:'—';
    [row.step??index,String(row.action||'hold').replaceAll('_',' '),precise(trajectoryBalance(row)),precise(row.reward),faults].forEach((value,column)=>tr.append(element('td',column===4&&faults!=='—'?'event-alert':'',value)));
    body.append(tr);
  });
  $('event-count').textContent=`${trajectory.length} STEPS`;
  $('scenario-results').hidden=false;
}

$('scenario-form').addEventListener('submit',async event=>{
  event.preventDefault();syncScenarioLimits();
  const steps=Number($('scenario-steps').value);
  const body={steps,seed:42,policy:$('scenario-policy').value};
  if($('fault-asset').value)body.faults=[{step:Number($('fault-step').value),asset_id:$('fault-asset').value,duration_steps:Number($('fault-duration').value)}];
  const button=$('scenario-run');button.disabled=true;$('scenario-error').hidden=true;$('scenario-results').hidden=true;
  $('scenario-status').textContent='Running deterministic scenario…';
  try{
    const data=await postJSON('/api/scenario',body);renderScenario(data);
    $('scenario-status').textContent=`Scenario complete · ${data.steps??data.trajectory?.length??steps} steps · Seed ${data.seed??42} · Synthetic simulator`;
  }catch(error){$('scenario-error').textContent=`Scenario failed: ${error.message}`;$('scenario-error').hidden=false;$('scenario-status').textContent='Scenario unavailable. Review the controls or retry.';
  }finally{button.disabled=false;}
});
