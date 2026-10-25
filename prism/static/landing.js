/* One deliberate brand reveal. Data, navigation and application readiness are independent. */
import { generate } from './vendor/prism-generation/ui-generation.js';

const logo=document.getElementById('prism-logo-animation');
const replay=document.getElementById('prism-logo-replay');
const status=document.getElementById('prism-logo-status');
let played=false;
let run=null;
let preparing=false;

async function revealLogo(){
  if(!logo||run||preparing)return;
  preparing=true;
  await document.fonts.ready;
  if(!logo.getBoundingClientRect().width){preparing=false;return;}
  replay.disabled=true;
  replay.setAttribute('aria-busy','true');
  logo.dataset.animation='playing';
  try{
    run=generate(logo,{variant:'ui',mode:'skeleton'});
    await run.finished;
    logo.dataset.animation='complete';
  }catch{
    // The static brand remains the fallback if drawing is unavailable.
    logo.style.opacity='';logo.style.clipPath='';logo.style.filter='';
    logo.dataset.animation='static';
  }finally{
    run=null;preparing=false;replay.disabled=false;replay.setAttribute('aria-busy','false');
    status.textContent='';
  }
}

if(logo&&replay){
  const observer=new IntersectionObserver(entries=>{
    if(played||!entries.some(entry=>entry.isIntersecting))return;
    played=true;observer.disconnect();revealLogo();
  },{threshold:.5});
  observer.observe(logo);
  replay.addEventListener('click',revealLogo);
  // A resize invalidates the runtime's measured drawing; reveal the static logo immediately.
  window.addEventListener('resize',()=>run?.cancel(),{passive:true});
  window.addEventListener('pagehide',()=>run?.cancel());
}
