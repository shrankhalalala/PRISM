'use strict';
const $ = id => document.getElementById(id);
const number = value => Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-IN', {maximumFractionDigits: 1}) : '—';
let liveRequestPending = false;
let lastLiveSnapshot = null;
let lastLiveReceivedAt = 0;
let liveRequestFailed = false;
function renderLiveGrid() {
  const data = lastLiveSnapshot;
  const reading = data?.reading;
  [['demand','demand_mw'],['frequency','frequency_hz'],['drawal','drawal_mw'],['schedule','schedule_mw']].forEach(([id,key]) => {
    const value = reading?.[key];
    $(`live-${id}`).closest('article').dataset.availability=typeof value==='number'&&Number.isFinite(value)?'available':'unknown';
    $(`live-${id}`).textContent = typeof value === 'number' && Number.isFinite(value)
      ? value.toLocaleString('en-IN', {maximumFractionDigits: id === 'frequency' ? 3 : 1}) : '—';
  });
  const age = data?.age_seconds == null ? null : data.age_seconds + (Date.now()-lastLiveReceivedAt)/1000;
  const stale = liveRequestFailed || data?.status !== 'live' || age > 300;
  $('live-status').textContent = !reading
    ? 'Unavailable · Delhi SLDC could not be reached or has no valid reading. Retrying every minute.'
    : liveRequestFailed ? 'Refresh failed · showing the last available reading with its original source time. Retrying every minute.'
    : stale ? 'Stale · Last available Delhi SLDC reading. Waiting for a fresh source update.'
    : 'Delhi SLDC · checks every minute.';
  const sourceState=!reading?'unavailable':stale?'stale':'live';
  $('live-status').dataset.state=sourceState;
  $('live-state-label').dataset.state=sourceState;
  $('live-state-label').textContent=!reading?'Unavailable':stale?'Stale reading':'Published reading';
  document.querySelector('.live-metrics').dataset.state=sourceState;
  $('live-timestamp').textContent = reading
    ? `Source timestamp: ${new Date(reading.observed_at).toLocaleString('en-IN', {timeZone:'Asia/Kolkata',hour12:false})} IST · Reading age: ${Math.floor(age)} seconds`
    : 'Source timestamp: no valid reading received.';
}
async function loadLiveGrid() {
  if (liveRequestPending || document.hidden) return;
  liveRequestPending = true;
  $('live-refresh').disabled=true;$('live-refresh').setAttribute('aria-busy','true');$('live-refresh').textContent='Refreshing…';document.querySelector('.live-metrics').setAttribute('aria-busy','true');
  $('live-status').textContent=lastLiveSnapshot?.reading?'Refreshing published readings · previous values retain their source time.':'Connecting to the published Delhi SLDC feed…';
  try {
    const response = await fetch('/api/live/gridwatch', {signal:AbortSignal.timeout(12000),cache:'no-store'});
    const data = await response.json();
    if (!['live','stale','unavailable'].includes(data.status) || (!response.ok && response.status !== 503)) throw new Error('Invalid live response');
    if(data.reading||!lastLiveSnapshot?.reading){lastLiveSnapshot=data;lastLiveReceivedAt=Date.now();liveRequestFailed=false;}else liveRequestFailed=true;
  } catch {
    liveRequestFailed = true;
  } finally {
    renderLiveGrid();
    liveRequestPending = false;
    $('live-refresh').disabled=false;$('live-refresh').setAttribute('aria-busy','false');$('live-refresh').textContent='Refresh readings';document.querySelector('.live-metrics').setAttribute('aria-busy','false');
  }
}
let activeSeries = 'demand_mw';
let activeHours = 24;
let measurementData = null;
let measurementRequest = 0;
const seriesNames = {demand_mw:'Demand',solar_mw:'Solar',wind_mw:'Wind'};
const preferences = {get(key){try{return localStorage.getItem(key);}catch{return null;}},set(key,value){try{localStorage.setItem(key,value);}catch{}}};
const mobileQuery=matchMedia('(max-width:640px)');
let desktopCollapsed=preferences.get('prism-terminal-nav-expanded')!=='true';
let drawerOpen=false;
function updateSidebar(){
  const expanded=!mobileQuery.matches&&!desktopCollapsed;
  document.body.classList.toggle('sidebar-collapsed',!expanded);
  document.body.classList.remove('drawer-open');
  $('sidebar').inert=false;$('sidebar').setAttribute('aria-hidden','false');
  $('sidebar-toggle').setAttribute('aria-expanded',String(expanded));
  $('sidebar-toggle').setAttribute('aria-label',expanded?'Collapse navigation':'Expand navigation');
  $('sidebar-backdrop').hidden=true;$('main').inert=false;document.querySelector('.topbar-actions').inert=false;
}
const researchTabs=Array.from(document.querySelectorAll('[data-research-tab]'));
let activeResearchPanel='simulation';
function selectResearchPanel(name){
  if(!researchTabs.some(tab=>tab.dataset.researchTab===name))return;
  activeResearchPanel=name;
  document.querySelectorAll('[data-research-panel]').forEach(panel=>{const active=panel.dataset.researchPanel===name;panel.hidden=!active;panel.inert=!active;});
  researchTabs.forEach(tab=>{const active=tab.dataset.researchTab===name;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;});
}
function highlightRegion(section){
  document.querySelectorAll('#sidebar nav a').forEach(link=>{const active=link.getAttribute('href')===`#${section}`;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');});
  $('breadcrumb-section').textContent=document.querySelector(`#sidebar nav a[href="#${section}"]`)?.dataset.navLabel||'Home';
}
function updateActiveNavigation(){
  let requested=location.hash.slice(1);
  if(!requested||requested==='overview'||requested==='live-grid'){requested='home';history.replaceState(null,'','#home');}
  const target=document.getElementById(requested)||$('home');
  const panel=target.closest('[data-research-panel]');
  if(panel)selectResearchPanel(panel.dataset.researchPanel);
  const section=target.closest('main>.workspace-section')?.id||'home';
  highlightRegion(section);
  for(let parent=target.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
  const destination=target.matches('[data-research-panel]')?$('research-tabs'):target;
  requestAnimationFrame(()=>destination.scrollIntoView({block:'start'}));
}
researchTabs.forEach((tab,index)=>{
  tab.addEventListener('click',()=>{
    const hash='#'+tab.getAttribute('aria-controls');
    if(location.hash!==hash)history.pushState(null,'',hash);
    updateActiveNavigation();
    tab.focus({preventScroll:true});
  });
  tab.addEventListener('keydown',event=>{
    let next;if(event.key==='ArrowRight'||event.key==='ArrowDown')next=(index+1)%researchTabs.length;else if(event.key==='ArrowLeft'||event.key==='ArrowUp')next=(index-1+researchTabs.length)%researchTabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=researchTabs.length-1;else return;
    event.preventDefault();researchTabs[next].focus({preventScroll:true});researchTabs[next].click();
  });
});
selectResearchPanel(activeResearchPanel);
$('sidebar-toggle').addEventListener('click',()=>{if(mobileQuery.matches)return;desktopCollapsed=!desktopCollapsed;preferences.set('prism-terminal-nav-expanded',String(!desktopCollapsed));updateSidebar();});
mobileQuery.addEventListener('change',updateSidebar);
document.addEventListener('keydown',event=>{const status=$('system-status');if(event.key==='Escape'&&status.open){status.open=false;status.querySelector('summary').focus();}});
updateSidebar();
window.addEventListener('hashchange',updateActiveNavigation);
window.addEventListener('popstate',updateActiveNavigation);
let regionFrame=0;window.addEventListener('scroll',()=>{if(regionFrame)return;regionFrame=requestAnimationFrame(()=>{regionFrame=0;let region='home';document.querySelectorAll('main>.workspace-section').forEach(section=>{if(section.getBoundingClientRect().top<=160)region=section.id;});highlightRegion(region);});},{passive:true});
updateActiveNavigation();
const darkQuery=matchMedia('(prefers-color-scheme:dark)');
let explicitTheme=preferences.get('prism-theme');
function setTheme(theme){
  document.documentElement.dataset.theme=theme;const dark=theme==='dark';
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',dark?'#111315':'#edf1f4');
  const icon=document.createElementNS('http://www.w3.org/2000/svg','svg');icon.setAttribute('class','ui-icon');icon.setAttribute('viewBox','0 0 24 24');icon.setAttribute('fill','none');icon.setAttribute('stroke','currentColor');icon.setAttribute('stroke-width','1.6');icon.setAttribute('stroke-linecap','round');icon.setAttribute('stroke-linejoin','round');
  const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',dark?'M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z':'M20 15.5A8.5 8.5 0 0 1 8.5 4a8.5 8.5 0 1 0 11.5 11.5Z');icon.append(path);$('theme-icon').replaceChildren(icon);
  $('theme-label').textContent=dark?'Light':'Dark';$('theme-toggle').setAttribute('aria-label',`Switch to ${dark?'light':'dark'} theme`);
}
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
function renderMeasurements(data) {
  measurementData=data;
  $('record-count').textContent=`${data.records.length} hourly records`;
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
  $('measurement-refresh').disabled=true;
  $('chart-status').textContent=`Loading ${activeHours===24?'24-hour':'7-day'} sample…`;
  $('measurement-chart').setAttribute('aria-busy','true');
  document.querySelectorAll('button[data-hours]').forEach(button=>button.disabled=true);
  try{
    const data=await getJSON(`/api/measurements?limit=${activeHours}`);
    if(request!==measurementRequest)return;
    renderMeasurements(data);
    document.querySelectorAll('button[data-hours]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.hours)===activeHours)));
    $('chart-status').textContent='Synthetic history loaded · Select a series to explore';
  }catch(error){if(request===measurementRequest)$('chart-status').textContent='Measurements could not be loaded. Previous chart, if present, is unchanged. Use Refresh measurements to retry.';throw error;
  }finally{if(request===measurementRequest){$('measurement-refresh').disabled=false;document.querySelectorAll('button[data-hours]').forEach(button=>button.disabled=false);$('measurement-chart').setAttribute('aria-busy','false');}}
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
async function loadScenarioAssets(){
  $('scenario-assets-retry').disabled=true;
  $('scenario-fixture-status').textContent='Loading synthetic fault-injection assets…';
  try{
    populateFaultAssets(await getJSON('/api/grid'));
    $('scenario-fixture-status').textContent='Synthetic fixture assets · used only for scenario fault injection.';
  }catch{
    $('scenario-fixture-status').textContent='Simulation assets unavailable. Retry loading to configure fault injection.';
  }finally{$('scenario-assets-retry').disabled=false;}
}
$('measurement-refresh').addEventListener('click',()=>loadMeasurements().catch(()=>{}));
$('scenario-assets-retry').addEventListener('click',loadScenarioAssets);
loadMeasurements().catch(()=>{});
loadScenarioAssets();

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
  $('forecast-result-label').textContent=`${predictions.length}-hour outlook`;
  $('forecast-result-model').textContent=modelNames[model]||model;
  const list=$('forecast-values');list.replaceChildren();
  predictions.forEach((value,index)=>{const item=element('li');item.append(element('span','',`T + ${index+1} h`),element('strong','',precise(value)));list.append(item);});
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
  $('event-count').textContent=`${trajectory.length} steps`;
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

$('live-refresh').addEventListener('click',loadLiveGrid);
loadLiveGrid();
setInterval(loadLiveGrid,60000);
setInterval(()=>{if (!document.hidden && lastLiveSnapshot) renderLiveGrid();},10000);
document.addEventListener('visibilitychange',()=>{if (!document.hidden) loadLiveGrid();});
