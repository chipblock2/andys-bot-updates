let deferredInstallPrompt=null;
const installBtn=document.getElementById('installBtn');
function routeFromHash(){const name=(location.hash||'').replace('#','').toLowerCase();if(['home','explore','family','saved','more'].includes(name)){const nav=document.querySelector(`.nav[data-view="${name}"]`);if(nav)nav.click();}}
window.addEventListener('hashchange',routeFromHash);
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();deferredInstallPrompt=event;if(installBtn)installBtn.hidden=false;});
if(installBtn){installBtn.addEventListener('click',async()=>{if(!deferredInstallPrompt)return;deferredInstallPrompt.prompt();await deferredInstallPrompt.userChoice;deferredInstallPrompt=null;installBtn.hidden=true;});}
window.addEventListener('appinstalled',()=>{deferredInstallPrompt=null;if(installBtn)installBtn.hidden=true;});

if(typeof scorePlace==='function'){
  const originalScorePlace=scorePlace;
  scorePlace=function(...args){const result=originalScorePlace(...args);return result?.opening?.state==='closed'?null:result;};
}

const searchStopWords=new Set(['what','whats','what’s','on','near','me','in','at','the','a','an','find','show','for','to','do','is','are','this','with','please']);
function plusDays(day,n){const d=new Date(day+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);}
function smartExplore(){
  const raw=document.getElementById('exploreAsk').value.trim();
  const q=raw.toLowerCase();
  const all=[...EVENTS.map(normEvent),...PLACES.map(normPlace)].filter(x=>x.status==='Published');
  const today=todayLondon();
  const requestedDay=q.includes('tomorrow')?plusDays(today,1):(q.includes('today')?today:null);
  const town=Object.keys(TOWNS).find(t=>q.includes(t.toLowerCase()));
  let matches=all.filter(x=>{
    if(requestedDay&&x.type==='event'&&!onDate(x,requestedDay))return false;
    if(town&&String(x.town||'').toLowerCase().indexOf(town.toLowerCase())<0)return false;
    return true;
  });
  if(/\bfree\b|cheap|budget/.test(q))matches=matches.filter(x=>x.price_from===0||x.price_level==='Free'||x.price_level==='£'||(x.price_from!=null&&x.price_from<=10));
  if(/indoor|rain|raining/.test(q))matches=matches.filter(x=>/indoor|mixed/i.test(String(x.indoor_outdoor||'')));
  if(/family|kids|children|child/.test(q))matches=matches.filter(x=>x.family_friendly||(x.audience||[]).some(v=>/famil|child/i.test(v))||['Family','Workshop'].includes(x.category));
  const tokens=q.replace(/[’']/g,'').split(/[^a-z0-9]+/).filter(t=>t.length>=3&&!searchStopWords.has(t)&&!['today','tomorrow'].includes(t)&&!(town&&town.toLowerCase().includes(t)));
  if(tokens.length){matches=matches.filter(x=>{const hay=searchable(x);return tokens.some(t=>hay.includes(t));});}
  matches.sort((a,b)=>{if(requestedDay&&a.type!==b.type)return a.type==='event'?-1:1;return Number(b.featured||0)-Number(a.featured||0);});
  EXPLORE_ITEMS=matches.slice(0,40);
  document.getElementById('exploreResults').innerHTML=EXPLORE_ITEMS.length?EXPLORE_ITEMS.map(x=>card(x)).join(''):'<div class="empty">No matching live listings yet.</div>';
  if(document.getElementById('mapWrap').classList.contains('show'))renderMap(EXPLORE_ITEMS);
}
if(typeof runExplore==='function')runExplore=smartExplore;
const exploreBtn=document.getElementById('exploreBtn');
if(exploreBtn)exploreBtn.onclick=smartExplore;
const exploreAsk=document.getElementById('exploreAsk');
if(exploreAsk)exploreAsk.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();smartExplore();}});

function injectCommunityTools(){
  const quick=document.querySelector('#homeView .quick');
  if(quick&&!quick.querySelector('[data-community="deals"]'))quick.insertAdjacentHTML('beforeend','<button data-community="deals"><b>🏷 Deals & offers</b><span>Current local offers, with sponsored promotions clearly labelled.</span></button>');
  quick?.querySelector('[data-community="deals"]')?.addEventListener('click',()=>location.href='deals.html');
  const moreCards=document.querySelector('#moreView .cards');
  if(moreCards&&!document.getElementById('communityActionsCard'))moreCards.insertAdjacentHTML('afterbegin',`<div class="card" id="communityActionsCard"><h3>Take part</h3><p class="desc">Submit a local event, manage a business listing, choose useful alerts or browse current deals.</p><div class="buttons"><a class="mini go" href="submit-event.html">Submit event</a><a class="mini" href="claim-business.html">Claim business</a><a class="mini" href="update-business.html">Update claimed listing</a><a class="mini" href="alerts.html">Alerts</a><a class="mini" href="deals.html">Deals</a></div></div>`);
}
injectCommunityTools();

if('serviceWorker' in navigator){
  window.addEventListener('load',async()=>{
    try{
      const reg=await navigator.serviceWorker.register('./sw.js',{scope:'./'});
      reg.addEventListener('updatefound',()=>{
        const worker=reg.installing;if(!worker)return;
        worker.addEventListener('statechange',()=>{
          if(worker.state==='installed'&&navigator.serviceWorker.controller){
            const status=document.getElementById('status');
            if(status)status.textContent='A new Ask Shropshire version is ready. Reopen the app to use it.';
          }
        });
      });
    }catch(e){console.warn('Service worker registration failed',e);}
    routeFromHash();
  });
} else {window.addEventListener('load',routeFromHash);}
