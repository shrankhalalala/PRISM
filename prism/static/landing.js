/* Brand-only loop; data readiness and navigation never wait for animation. */
import { generate } from './vendor/prism-generation/ui-generation.js';
const logo=document.getElementById('prism-logo-animation');
const motion=matchMedia('(prefers-reduced-motion: reduce)');
let visible=false,active=true,run=null,preparing=false,timer=null,resizeTimer=null,resizing=false,cycles=0;
const eligible=()=>logo&&visible&&active&&!document.hidden&&!motion.matches&&!resizing;
function clearTimer(){clearTimeout(timer);timer=null;}
function pause(){clearTimer();run?.cancel();if(logo)logo.dataset.animation='static';}
function schedule(delay=3000){clearTimer();if(eligible()&&!run&&!preparing)timer=setTimeout(play,delay);}
async function play(){
 if(!eligible()||run||preparing)return;
 preparing=true;
 try{
  await document.fonts.ready;
  if(!eligible()||!logo.getBoundingClientRect().width)return;
  logo.dataset.animation='playing';
  const current=generate(logo,{variant:'ui',mode:'skeleton'});run=current;
  await current.finished;
  if(eligible()){cycles++;logo.dataset.completedCycles=String(cycles);logo.dataset.animation='complete';}
 }catch{logo.dataset.animation='static';}
 finally{run=null;preparing=false;schedule();}
}
if(logo){
 const observer=new IntersectionObserver(entries=>{visible=entries.some(entry=>entry.isIntersecting);if(visible)schedule(0);else pause();},{threshold:.25});
 observer.observe(logo.closest('.landing-logo')||logo);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();else schedule(0);});
 motion.addEventListener('change',()=>{if(motion.matches)pause();else schedule(0);});
 window.addEventListener('resize',()=>{resizing=true;pause();clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{resizing=false;schedule(0);},180);},{passive:true});
 window.addEventListener('pagehide',()=>{active=false;clearTimeout(resizeTimer);resizing=false;pause();});
 window.addEventListener('pageshow',()=>{active=true;resizing=false;schedule(0);});
}
