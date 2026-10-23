/* Human review and synthetic worker controls; never sends equipment commands. */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  if(!$('operations'))return;
  const actions=['hold','increase_generation','decrease_generation','charge_battery','discharge_battery','shed_load'];
  const state={job:null,advisory:null,polling:false,canceling:false,jobVersion:0,submitting:false,refreshing:false,timer:null};
  const label=value=>String(value??'Unknown').replaceAll('_',' ');
  const num=value=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(undefined,{maximumFractionDigits:5}):'Unknown';
  const date=value=>{const d=new Date(value);return value&&!Number.isNaN(d.valueOf())?d.toLocaleString('en-IN',{timeZone:'Asia/Kolkata',hour12:false})+' IST':'Unknown source time';};
  function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
  function error(id,message){$(id).hidden=!message;$(id).textContent=message||'';}
  function facts(target,entries){target.replaceChildren();entries.forEach(([name,value])=>{const row=node('div');row.append(node('dt',name),node('dd',value));target.append(row);});}
  async function api(path,method='GET',body){
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);
    const headers={Accept:'application/json'};
    if(body!==undefined)headers['Content-Type']='application/json';
    const token=$('ops-token').value.trim();if(method!=='GET'&&token)headers['X-PRISM-Operator-Token']=token;
    try{
      const response=await fetch(path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal,cache:'no-store'});
      const data=await response.json().catch(()=>({}));
      if(!response.ok){const code=String(data.error||data.error_code||response.status);throw new Error(response.status===401||response.status===403?'Operator authorization failed. Enter the configured token and retry.':response.status===503?'Service unavailable. Check service health, then retry. '+label(code):'Request failed: '+label(code)+(data.message?' · '+String(data.message):'')+'. Review inputs and retry.');}
      return data;
    }catch(err){if(err.name==='AbortError')throw new Error('Request timed out. Check service health and existing records before retrying.');if(err instanceof TypeError)throw new Error('Connection failed. Check service health and retry.');throw err;}finally{clearTimeout(timer);}
  }
  actions.forEach(action=>{
    const wrap=node('label'),input=node('input');input.type='checkbox';input.value=action;input.checked=true;wrap.append(input,node('span',label(action)));$('ops-valid-actions').append(wrap);
    const option=node('option',label(action));option.value=action;$('ops-override').append(option);
  });
  async function refresh(){
    if(state.refreshing)return;state.refreshing=true;$('ops-refresh').disabled=true;
    $('ops-health').textContent='Checking services…';$('ops-alert-status').textContent='Checking alerts…';
    await Promise.allSettled([
      api('/api/operations/health').then(data=>{
        const services=Object.entries(data.services||{}).map(([key,value])=>label(key)+': '+label(typeof value==='object'?(value?.status??'unknown'):value));
        $('ops-health').textContent=label(data.status)+' · '+services.join(' · ');$('ops-health').dataset.status=data.status;
      }).catch(err=>{$('ops-health').textContent=err.message;$('ops-health').dataset.status='unavailable';}),
      api('/api/alerts').then(data=>{
        $('ops-alert-list').replaceChildren();const alerts=Array.isArray(data.alerts)?data.alerts:[];
        $('ops-alert-status').textContent=alerts.length?alerts.length+' alert(s) · '+label(data.status):data.status==='ok'?'No alerts reported at this check.':'No alert records available · '+label(data.status)+'. Refresh to retry.';
        $('ops-alert-time').textContent='Checked '+date(data.checked_at);
        alerts.forEach(a=>{const item=node('li');item.append(node('strong',label(a.severity)+' / '+label(a.category)),node('p',a.message),node('small',date(a.observed_at)+' · '+label(a.data_source)+(a.asset_id?' · '+a.asset_id:'')));$('ops-alert-list').append(item);});
      }).catch(err=>{$('ops-alert-status').textContent=err.message+' Use Refresh services to retry.';$('ops-alert-time').textContent='Check failed';$('ops-alert-list').replaceChildren();})
    ]);state.refreshing=false;$('ops-refresh').disabled=false;
  }
  const activeJob=()=>state.job&&['queued','running'].includes(state.job.status);
  const jobLabel=kind=>kind==='forecast'?'Demand forecast refresh':kind==='retrain'?'Retraining review':'Synthetic scenario';
  function jobButtons(busy){['ops-job-run','ops-forecast-queue','ops-retrain-queue'].forEach(id=>$(id).disabled=busy);}
  function jobView(job){
    state.job=job;$('ops-job-status').textContent=jobLabel(job.kind)+' · '+label(job.status)+' · ID '+job.id+(job.attempts!==undefined?' · attempts '+job.attempts:'')+(job.progress!==undefined?' · progress '+job.progress+'%':'');
    $('ops-job-poll').disabled=false;$('ops-job-cancel').disabled=!activeJob();jobButtons(!!activeJob());
    $('ops-job-result').hidden=job.status!=='succeeded';
    if(job.status==='succeeded'){
      $('ops-job-result-title').textContent=jobLabel(job.kind)+' result';
      const result=job.result??{};if(job.kind==='retrain'&&typeof result.promoted==='boolean')$('ops-job-result-title').textContent=result.promoted?'Validation gate passed · candidate promoted':'Validation gate not passed · current model retained';
      const summary=result.totals??result.summary??result.metrics??result;
      const totalLabels={return:'Cumulative reward',unserved_mwh:'Unserved · MWh',curtailed_mwh:'Curtailed · MWh',operating_cost:'Cost · synthetic units',emissions_kg:'Emissions · kg CO₂e'};
      facts($('ops-job-summary'),Object.entries(summary).filter(([,v])=>['number','string','boolean'].includes(typeof v)).slice(0,12).map(([k,v])=>[totalLabels[k]||label(k),typeof v==='number'?num(v):String(v)]));
      $('ops-job-json').textContent=JSON.stringify(result,null,2);
    }
    if(job.status==='failed')error('ops-job-error','Job failed: '+label(job.error_code||'unknown error')+'. Check services; queue a new experiment to retry.');
    if(activeJob()&&!document.hidden){clearTimeout(state.timer);state.timer=setTimeout(pollJob,2000);}else clearTimeout(state.timer);
  }
  async function pollJob(){
    if(!state.job||state.polling||state.canceling)return;const version=state.jobVersion;state.polling=true;$('ops-job-poll').disabled=true;
    try{const data=await api('/api/jobs/'+encodeURIComponent(state.job.id));if(version!==state.jobVersion)return;error('ops-job-error','');jobView(data);}catch(err){if(version!==state.jobVersion)return;error('ops-job-error',err.message+' Use Check job to retry.');clearTimeout(state.timer);}finally{state.polling=false;$('ops-job-poll').disabled=false;}
  }
  async function queueJob(kind,request){
    if(activeJob()||state.submitting)return;state.submitting=true;jobButtons(true);error('ops-job-error','');$('ops-job-status').textContent='Submitting '+jobLabel(kind).toLowerCase()+'…';$('ops-job-result').hidden=true;
    try{jobView(await api('/api/jobs','POST',{kind,request}));}
    catch(err){error('ops-job-error',err.message);$('ops-job-status').textContent='Job submission was not confirmed.';}finally{state.submitting=false;jobButtons(!!activeJob());}
  }
  $('ops-job-form').addEventListener('submit',event=>{event.preventDefault();queueJob('scenario',{steps:Number($('ops-job-steps').value),seed:Number($('ops-job-seed').value),policy:$('ops-job-policy').value});});
  $('ops-forecast-queue').addEventListener('click',()=>queueJob('forecast',{}));
  $('ops-retrain-queue').addEventListener('click',()=>queueJob('retrain',{}));
  $('ops-job-poll').addEventListener('click',pollJob);
  $('ops-job-cancel').addEventListener('click',async()=>{
    if(!activeJob()||state.canceling)return;state.canceling=true;state.jobVersion++;$('ops-job-cancel').disabled=true;clearTimeout(state.timer);error('ops-job-error','');
    try{jobView(await api('/api/jobs/'+encodeURIComponent(state.job.id)+'/cancel','POST',{}));}catch(err){error('ops-job-error',err.message);$('ops-job-cancel').disabled=!activeJob();}finally{state.canceling=false;}
  });
  function renderAdvisory(data){
    const rec=data.recommendation||{},target=$('ops-recommendation');target.replaceChildren();
    const headline=node('div',undefined,'ops-recommendation');headline.append(node('span','Q-POLICY RECOMMENDATION','small-label'),node('strong',label(rec.recommended_action)),node('span',rec.abstained?'SURROGATE ABSTAINS · REVIEW REQUIRED':'HUMAN REVIEW REQUIRED','ops-review-flag'));target.append(headline);
    const detail=node('dl',undefined,'ops-facts');facts(detail,[['Q-policy action',label(rec.q_action)],['Surrogate action',label(rec.surrogate_action)],['Agreement',rec.agreement?'Agrees with Q-policy':'Disagrees with Q-policy'],['Surrogate score',num(rec.score)+' · uncalibrated, not a probability of safe operation'],['Abstention threshold',num(rec.threshold)],['Explained action',label(rec.explained_action)],['Source',label(data.data_source||rec.data_source)],['Executable','No · advisory record only']]);target.append(detail);
    if(rec.abstained)target.append(node('p','Surrogate confidence is below its threshold. The Q-policy action remains visible for review; this is not an operational clearance.','ops-warning'));
    if(rec.limitation)target.append(node('p',rec.limitation,'ops-copy'));
    $('ops-factors').replaceChildren();(rec.factors||[]).forEach(f=>{const row=node('li');const head=node('div');head.append(node('strong',label(f.feature)),node('span',(f.contribution>0?'+':'')+num(f.contribution)));row.append(head,node('p',f.explanation),node('small','Input value '+num(f.value)+' · '+label(f.direction)));$('ops-factors').append(row);});
    if(!rec.factors?.length)$('ops-factors').append(node('li','No attribution factors returned.'));
    facts($('ops-provenance'),[['Method',rec.method||'Unknown'],['Output space',label(rec.output_space)],['Base value',num(rec.base_value)],['Raw margin',num(rec.raw_margin)],['Additivity residual',typeof rec.additivity_residual==='number'?String(rec.additivity_residual):'Unknown'],['Background samples',num(rec.background_samples)],['Q-policy SHA-256',rec.q_policy_sha256||'Unknown'],['Surrogate SHA-256',rec.surrogate_sha256||'Unknown'],['Background SHA-256',rec.background_sha256||'Unknown']]);
    const valid=rec.valid_actions||actions;Array.from($('ops-override').options).forEach(o=>o.disabled=!valid.includes(o.value));$('ops-override').value=valid[0]||'';
    $('ops-advisory-result').hidden=false;$('ops-advisory-status').textContent='Advisory '+data.id+' · generated for your supplied inputs. Review before recording a decision.';
  }
  $('ops-advisory-form').addEventListener('submit',async event=>{
    event.preventDefault();const valid=Array.from($('ops-valid-actions').querySelectorAll('input:checked')).map(input=>input.value);error('ops-advisory-error','');
    if(!valid.length){error('ops-advisory-error','Select at least one candidate action.');return;}
    $('ops-advisory-run').disabled=true;$('ops-advisory-status').textContent='Generating advisory and TreeSHAP explanation…';$('ops-advisory-result').hidden=true;state.advisory=null;
    try{const data=await api('/api/advisories','POST',{observation:{demand_mw:Number($('ops-demand').value),generation_mw:Number($('ops-generation').value),reserve_mw:Number($('ops-reserve').value),battery_soc:Number($('ops-battery').value),renewable_trend:Number($('ops-trend').value),fault_present:$('ops-fault').value==='true'},valid_actions:valid});state.advisory=data;$('ops-decision-form').reset();$('ops-override-label').hidden=true;$('ops-decision-status').textContent='';error('ops-decision-error','');renderAdvisory(data);await loadDecisions();}
    catch(err){error('ops-advisory-error',err.message);$('ops-advisory-status').textContent='Advisory generation was not confirmed. No decision has been recorded.';}finally{$('ops-advisory-run').disabled=false;}
  });
  $('ops-decision').addEventListener('change',()=>{$('ops-override-label').hidden=$('ops-decision').value!=='override';});
  async function loadDecisions(){
    if(!state.advisory)return;const id=state.advisory.id;$('ops-decisions-refresh').disabled=true;
    try{const data=await api('/api/advisories/'+encodeURIComponent(id)+'/decisions');if(state.advisory?.id!==id)return;$('ops-decisions').replaceChildren();(data.records||[]).forEach(record=>{const item=node('li');item.append(node('strong',label(record.decision)+' · '+label(record.chosen_action)),node('p',record.reason),node('small',record.operator+' · '+date(record.created_at)+' · '+record.id));$('ops-decisions').append(item);});if(!data.records?.length)$('ops-decisions').append(node('li','No decisions recorded for this advisory.'));}
    catch(err){error('ops-decision-error',err.message+' Use Refresh history to retry.');}finally{$('ops-decisions-refresh').disabled=false;}
  }
  $('ops-decision-form').addEventListener('submit',async event=>{
    event.preventDefault();if(!state.advisory)return;const operator=$('ops-operator').value.trim(),reason=$('ops-reason').value.trim();error('ops-decision-error','');
    if(!operator||!reason){error('ops-decision-error','Provide an operator name and a reason before recording your decision.');return;}
    const body={decision:$('ops-decision').value,operator,reason};if(body.decision==='override')body.override_action=$('ops-override').value;
    const advisoryId=state.advisory.id;
    $('ops-decision-save').disabled=true;$('ops-advisory-run').disabled=true;$('ops-decision-status').textContent='Saving human decision…';
    try{const record=await api('/api/advisories/'+encodeURIComponent(advisoryId)+'/decisions','POST',body);$('ops-decision-status').textContent='Recorded '+label(record.decision)+' · '+label(record.chosen_action)+' · audit ID '+record.id+'. No equipment command was sent.';await loadDecisions();}
    catch(err){error('ops-decision-error',err.message);$('ops-decision-status').textContent='Decision save was not confirmed. Refresh history before retrying.';}finally{$('ops-decision-save').disabled=false;$('ops-advisory-run').disabled=false;}
  });
  $('ops-decisions-refresh').addEventListener('click',()=>{error('ops-decision-error','');loadDecisions();});
  let forecasting=false;
  const svgNS='http://www.w3.org/2000/svg';
  function svgNode(tag,attrs,text){const element=document.createElementNS(svgNS,tag);Object.entries(attrs).forEach(([k,v])=>element.setAttribute(k,String(v)));if(text!==undefined)element.textContent=text;return element;}
  function forecastChart(data){
    const chart=$('ops-forecast-chart');chart.replaceChildren();
    const predictions=data.predictions,interval=data.interval;
    const values=[...predictions,...(interval?.lower_mw||[]),...(interval?.upper_mw||[])].filter(Number.isFinite);
    let lo=Math.min(...values),hi=Math.max(...values);const pad=Math.max((hi-lo)*.12,50);lo=Math.max(0,lo-pad);hi+=pad;
    const x=i=>65+i*805/Math.max(1,predictions.length-1),y=v=>225-(v-lo)*195/(hi-lo);
    for(let i=0;i<4;i++){const value=lo+(hi-lo)*i/3,py=y(value);chart.append(svgNode('line',{x1:65,x2:870,y1:py,y2:py,class:'ops-chart-grid'}),svgNode('text',{x:55,y:py+4,'text-anchor':'end',class:'ops-chart-label'},Math.round(value).toLocaleString()));}
    chart.append(svgNode('text',{x:65,y:15,class:'ops-chart-label'},'MW'));
    if(interval?.lower_mw?.length===predictions.length&&interval?.upper_mw?.length===predictions.length){const points=interval.upper_mw.map((v,i)=>[x(i),y(v)]).concat(interval.lower_mw.map((v,i)=>[x(i),y(v)]).reverse());chart.append(svgNode('polygon',{points:points.map(p=>p.join(',')).join(' '),class:'ops-chart-band'}));}
    chart.append(svgNode('polyline',{points:predictions.map((v,i)=>x(i)+','+y(v)).join(' '),class:'ops-chart-line'}));
    [0,Math.floor((predictions.length-1)/2),predictions.length-1].forEach(i=>chart.append(svgNode('text',{x:x(i),y:250,'text-anchor':i===0?'start':i===predictions.length-1?'end':'middle',class:'ops-chart-label'},'+'+(i+1)+'h')));
  }
  async function loadForecast(){
    if(forecasting)return;forecasting=true;$('ops-forecast-load').disabled=true;$('ops-forecast-model').disabled=true;error('ops-forecast-error','');$('ops-forecast-status').textContent='Loading audited demand forecast…';$('ops-forecast-result').hidden=true;
    try{
      const model=$('ops-forecast-model').value,data=await api('/api/forecast/real'+(model==='selected'?'':'?model='+encodeURIComponent(model)));
      if(!Array.isArray(data.predictions)||!data.predictions.length||!data.predictions.every(Number.isFinite))throw new Error('No eligible predictions returned. Retry after checking source history.');
      $('ops-forecast-freshness').textContent=label(data.status);$('ops-forecast-freshness').dataset.status=data.status;
      const age=Number.isFinite(data.source_age_seconds)?num(Math.round(data.source_age_seconds/360)/10)+' hours':'Unknown';
      $('ops-forecast-origin').textContent='Source: Delhi SLDC · origin '+date(data.origin)+' · age at load '+age+' · model '+label(data.model);
      $('ops-forecast-status').textContent=data.predictions.length+' hourly demand predictions · research preview · loaded '+date(new Date().toISOString())+'.';
      const interval=data.interval;
      $('ops-forecast-interval').textContent=interval?'Shaded band: '+num(interval.nominal_coverage*100)+'% nominal coverage · '+label(interval.method)+'. Empirical prediction interval; coverage is not guaranteed.':'No prediction interval is available for this model. Point predictions alone do not describe uncertainty.';
      $('ops-forecast-caption').textContent='Delhi demand forecast in MW from '+date(data.origin)+'. '+label(data.status)+'. '+(interval?'Shaded band shows the empirical prediction interval.':'Point predictions only.');
      forecastChart(data);$('ops-forecast-values').replaceChildren();data.predictions.forEach((value,i)=>{const item=node('li');item.append(node('span',date(data.forecast_timestamps?.[i])),node('strong',num(value)+' MW'));if(interval)item.append(node('small','Interval '+num(interval.lower_mw?.[i])+'–'+num(interval.upper_mw?.[i])+' MW'));$('ops-forecast-values').append(item);});
      facts($('ops-forecast-provenance'),[['Data source',label(data.data_source)],['Training end',date(data.training_end)],['Hourly history SHA-256',data.hourly_sha256||'Unknown'],['History context SHA-256',data.history_context_sha256||'Unknown'],['Model artifact SHA-256',data.artifact_sha256||'Unknown'],['Limitation',data.limitation||'Research preview; no operational validation.']]);
      $('ops-forecast-result').hidden=false;
    }catch(err){error('ops-forecast-error',err.message);$('ops-forecast-status').textContent='Forecast unavailable. Choose a model and load again to retry.';}finally{forecasting=false;$('ops-forecast-load').disabled=false;$('ops-forecast-model').disabled=false;}
  }
  $('ops-forecast-form').addEventListener('submit',event=>{event.preventDefault();loadForecast();});
  const investigation={alarms:[],assets:{},busy:false,loading:0};
  const assetName=id=>investigation.assets.reference?.find(asset=>asset.id===id)?.name||id;
  async function loadAssets(){
    const mode='reference',version=++investigation.loading;$('ops-diag-asset').disabled=true;$('ops-alarm-add').disabled=true;$('ops-diag-assets-status').textContent='Loading eligible asset choices…';
    try{
      const data=await api('/api/reference-grid');if(version!==investigation.loading)return;
      const assets=(data.assets||[]).filter(asset=>!String(asset.reference_classification||'').startsWith('planned'));
      investigation.assets[mode]=assets.map(asset=>({id:asset.id,name:asset.name||asset.id})).sort((a,b)=>a.name.localeCompare(b.name));
      $('ops-diag-asset').replaceChildren();investigation.assets[mode].forEach(asset=>{const option=node('option',asset.name+' · '+asset.id);option.value=asset.id;$('ops-diag-asset').append(option);});
      $('ops-diag-asset').disabled=!assets.length;$('ops-alarm-add').disabled=!assets.length||investigation.alarms.length>=100;
      $('ops-diag-assets-status').textContent=assets.length+' eligible assets · '+'Dated Delhi reference connectivity; planned assets excluded.';
    }catch(err){if(version!==investigation.loading)return;$('ops-diag-assets-status').textContent=err.message+' Use Reload asset choices to retry.';}
  }
  function alarmsView(){
    $('ops-alarms').replaceChildren();$('ops-alarm-count').textContent=investigation.alarms.length+' / 100';$('ops-diag-run').disabled=!investigation.alarms.length||investigation.busy;$('ops-alarm-clear').disabled=!investigation.alarms.length||investigation.busy;$('ops-alarm-add').disabled=$('ops-diag-asset').disabled||investigation.alarms.length>=100||investigation.busy;
    investigation.alarms.forEach((alarm,i)=>{const item=node('li'),text=node('div');text.append(node('strong',assetName(alarm.asset_id)),node('small',date(alarm.observed_at)));const remove=node('button','Remove','ref-button');remove.type='button';remove.disabled=investigation.busy;remove.setAttribute('aria-label','Remove alarm '+(i+1)+' for '+assetName(alarm.asset_id));remove.addEventListener('click',()=>{investigation.alarms.splice(i,1);$('ops-diag-result').hidden=true;alarmsView();});item.append(text,remove);$('ops-alarms').append(item);});
    if(!investigation.alarms.length)$('ops-alarms').append(node('li','No alarms added.'));
  }
  $('ops-alarm-form').addEventListener('submit',event=>{
    event.preventDefault();error('ops-diag-error','');if(investigation.busy||investigation.alarms.length>=100)return;
    const stamp=$('ops-diag-time').value.trim(),parsed=new Date(stamp);
    if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/i.test(stamp)||Number.isNaN(parsed.valueOf())||parsed.valueOf()>Date.now()+120000){error('ops-diag-error','Enter a valid, nonfuture ISO timestamp with Z or a timezone offset such as +05:30.');return;}
    const id=$('ops-diag-asset').value;if(!id)return;investigation.alarms.push({asset_id:id,observed_at:stamp.replace(/z$/i,'Z')});$('ops-diag-result').hidden=true;alarmsView();$('ops-diag-status').textContent='Supplied alarms changed. Run investigation to rank their connections.';
  });
  $('ops-alarm-clear').addEventListener('click',()=>{investigation.alarms=[];$('ops-diag-result').hidden=true;alarmsView();$('ops-diag-status').textContent='Add at least one supplied alarm to begin.';});
  $('ops-diag-reload').addEventListener('click',loadAssets);
  $('ops-diag-run').addEventListener('click',async()=>{
    if(investigation.busy||!investigation.alarms.length)return;investigation.busy=true;alarmsView();$('ops-diag-reload').disabled=true;error('ops-diag-error','');$('ops-diag-status').textContent='Ranking graph investigation hypotheses…';$('ops-diag-result').hidden=true;
    try{
      const data=await api('/api/diagnose','POST',{dataset:'reference',alarms:investigation.alarms});
      $('ops-diag-limitation').textContent=data.limitation;$('ops-diag-status').textContent=data.hypotheses.length+' investigation hypotheses · supplied alarms '+data.alarms_received+'. Scores are heuristics, not probabilities.';
      facts($('ops-diag-summary'),[['Method',data.method],['Dataset',data.dataset],['PageRank L1 residual',String(data.pagerank_l1_change)],['PageRank convergence',data.pagerank_converged?'Converged within stated tolerance':'Fixed iterations ended before convergence'],['Iterations / damping',data.iterations+' / '+data.damping],['Elapsed',num(data.elapsed_ms)+' ms'],['Connection semantics',data.relationship_semantics]]);
      $('ops-diag-hypotheses').replaceChildren();data.hypotheses.forEach(h=>{const item=node('li'),head=node('div',undefined,'ops-section-heading');head.append(node('h4',assetName(h.asset_id)),node('strong','Heuristic score '+num(h.heuristic_score)));item.append(head,node('p',h.has_observed_alarm?'Has supplied alarm · '+date(h.first_observed_at):'No supplied alarm at this asset.','ops-copy'));
        const details=node('details'),paths=node('ol');details.append(node('summary','Inspect connection paths & timing'));
        h.paths.forEach(path=>{const record=node('li');record.append(node('p',path.path.map(assetName).join(' → ')),node('small','Alarm asset: '+assetName(path.alarm_asset)+' · evidence: '+path.connection_evidence.flat().join(', ')));paths.append(record);});
        details.append(node('p','Timing residual: '+(h.timing_residual_seconds===null?'not estimated':num(h.timing_residual_seconds)+' s')+' · fitted lag: '+(h.fitted_seconds_per_hop===null?'not estimated':num(h.fitted_seconds_per_hop)+' s/hop')+'. Equal hop delays are a heuristic.'),paths);item.append(details);$('ops-diag-hypotheses').append(item);});$('ops-diag-result').hidden=false;
    }catch(err){error('ops-diag-error',err.message);$('ops-diag-status').textContent='Investigation unavailable. Check supplied alarms and retry.';}finally{investigation.busy=false;$('ops-diag-reload').disabled=false;alarmsView();}
  });
  loadAssets();
  $('ops-refresh').addEventListener('click',refresh);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)clearTimeout(state.timer);else if(activeJob())pollJob();});
  refresh();
})();
