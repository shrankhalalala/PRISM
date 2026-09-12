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
function closeDrawer(){drawerOpen=false;updateSidebar();$('sidebar-toggle').focus();}
$('sidebar-toggle').addEventListener('click',()=>{if(mobileQuery.matches){drawerOpen=!drawerOpen;}else{desktopCollapsed=!desktopCollapsed;preferences.set('prism-sidebar-collapsed',String(desktopCollapsed));}updateSidebar();});
$('sidebar-backdrop').addEventListener('click',closeDrawer);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&drawerOpen)closeDrawer();});
$('sidebar').querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{if(mobileQuery.matches)closeDrawer();}));
mobileQuery.addEventListener('change',()=>{drawerOpen=false;updateSidebar();});
updateSidebar();
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
  if(!response.ok)throw new Error(`${path} returned ${response.status}`);
  return response.json();
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
