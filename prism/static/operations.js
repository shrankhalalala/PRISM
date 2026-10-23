/* Human review and synthetic worker controls; never sends equipment commands. */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  if(!$('operations'))return;
  const actions=['hold','increase_generation','decrease_generation','charge_battery','discharge_battery','shed_load'];
  const state={job:null,advisory:null,polling:false,canceling:false,jobVersion:0,refreshing:false,timer:null};
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
  function jobView(job){
    state.job=job;$('ops-job-status').textContent='Synthetic scenario · '+label(job.status)+' · ID '+job.id+(job.attempts!==undefined?' · attempts '+job.attempts:'')+(job.progress!==undefined?' · progress '+job.progress+'%':'');
    $('ops-job-poll').disabled=false;$('ops-job-cancel').disabled=!activeJob();$('ops-job-run').disabled=!!activeJob();
    $('ops-job-result').hidden=job.status!=='succeeded';
    if(job.status==='succeeded'){
      const result=job.result??{};const summary=result.totals??result.summary??result.metrics??result;
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
  $('ops-job-form').addEventListener('submit',async event=>{
    event.preventDefault();if(activeJob())return;$('ops-job-run').disabled=true;error('ops-job-error','');$('ops-job-status').textContent='Submitting synthetic scenario…';$('ops-job-result').hidden=true;
    try{jobView(await api('/api/jobs','POST',{kind:'scenario',request:{steps:Number($('ops-job-steps').value),seed:Number($('ops-job-seed').value),policy:$('ops-job-policy').value}}));}
    catch(err){error('ops-job-error',err.message);$('ops-job-status').textContent='Job submission was not confirmed.';}finally{$('ops-job-run').disabled=!!activeJob();}
  });
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
  $('ops-refresh').addEventListener('click',refresh);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)clearTimeout(state.timer);else if(activeJob())pollJob();});
  refresh();
})();
