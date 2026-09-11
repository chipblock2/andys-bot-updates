(()=>{
  const qs=id=>document.getElementById(id);
  const safe=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  function planItems(){
    const c=(typeof LAST_FAMILY!=='undefined'&&Array.isArray(LAST_FAMILY))?LAST_FAMILY:[];
    const A=c[0];
    const B=c.find(x=>x.id!==A?.id&&x.type!==A?.type)||c.find(x=>x.id!==A?.id);
    const C=c.find(x=>x.id!==A?.id&&x.id!==B?.id&&(x.price_from===0||x.price_level==='Free'||(x.price_from!=null&&x.price_from<=10)))||c.find(x=>x.id!==A?.id&&x.id!==B?.id);
    return [A,B,C].filter(Boolean);
  }
  function b64url(obj){
    const bytes=new TextEncoder().encode(JSON.stringify(obj));
    let bin='';bytes.forEach(b=>bin+=String.fromCharCode(b));
    return btoa(bin).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  }
  function unb64url(s){
    const pad=s.replace(/-/g,'+').replace(/_/g,'/');
    const bin=atob(pad+'==='.slice((pad.length+3)%4));
    const bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  }
  function currentPayload(){
    return {v:1,date:qs('date')?.value||'',arrival:qs('arrival')?.value||'11:00',area:qs('area')?.value||'Telford',items:planItems().map(x=>({type:x.type,id:x.id,name:x.name,town:x.town||''}))};
  }
  function shareUrl(){const u=new URL(location.href);u.searchParams.set('plan',b64url(currentPayload()));u.hash='family';return u.toString();}
  function shareText(){const p=currentPayload();return `Ask Shropshire day plan for ${p.date||'the selected day'} from ${p.area}:\n`+p.items.map((x,i)=>`${String.fromCharCode(65+i)}. ${x.name}${x.town?' — '+x.town:''}`).join('\n')+`\n${shareUrl()}`;}
  async function sharePlan(){const text=shareText();if(navigator.share){try{await navigator.share({title:'Ask Shropshire day plan',text,url:shareUrl()});return;}catch(e){}}try{await navigator.clipboard.writeText(text);alert('Plan copied to clipboard.');}catch(e){prompt('Copy your plan:',text);}}
  function whatsappPlan(){window.open('https://wa.me/?text='+encodeURIComponent(shareText()),'_blank','noopener');}
  async function copyPlanLink(){const u=shareUrl();try{await navigator.clipboard.writeText(u);alert('Share link copied.');}catch(e){prompt('Copy this link:',u);}}
  function escICS(s){return String(s||'').replace(/\\/g,'\\\\').replace(/,/g,'\\,').replace(/;/g,'\\;').replace(/\n/g,'\\n');}
  function icsStamp(d){return d.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');}
  function calendarPlan(){
    const p=currentPayload(),items=planItems();if(!items.length)return;
    const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Ask Shropshire//Day Plan//EN','CALSCALE:GREGORIAN'];
    items.forEach((x,i)=>{
      let start,end;
      if(x.type==='event'&&x.start){start=new Date(x.start);end=new Date(x.end||new Date(start.getTime()+((x.typical_duration_minutes||120)*60000)));}
      else{start=new Date(`${p.date}T${p.arrival||'11:00'}:00`);start=new Date(start.getTime()+i*150*60000);end=new Date(start.getTime()+((x.typical_duration_minutes||120)*60000));}
      lines.push('BEGIN:VEVENT',`UID:askshropshire-${x.type}-${x.id}@askshropshire`,`DTSTAMP:${icsStamp(new Date())}`,`DTSTART:${icsStamp(start)}`,`DTEND:${icsStamp(end)}`,`SUMMARY:${escICS(x.name)}`,`LOCATION:${escICS(x.venue||x.address||x.town||'Shropshire')}`,`DESCRIPTION:${escICS(x.description||'Ask Shropshire day plan')}`,`URL:${escICS(x.booking_url||x.website||x.source_url||location.href)}`,'END:VEVENT');
    });
    lines.push('END:VCALENDAR');
    const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([lines.join('\r\n')],{type:'text/calendar'}));a.download='ask-shropshire-day-plan.ics';document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},500);
  }
  function setChip(mode){document.querySelectorAll('[data-weather]').forEach(x=>x.classList.toggle('active',x.dataset.weather===mode));if(typeof weatherMode!=='undefined')weatherMode=mode;}
  function nextSelect(id,dir){const s=qs(id);if(!s)return;const i=s.selectedIndex;s.selectedIndex=Math.max(0,Math.min(s.options.length-1,i+dir));}
  function shiftTime(mins){const el=qs('arrival');if(!el)return;const [h,m]=el.value.split(':').map(Number);let t=(h*60+m+mins+1440)%1440;el.value=String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0');}
  function nextSaturday(date){const d=new Date((date||new Date().toISOString().slice(0,10))+'T12:00:00Z');let add=(6-d.getUTCDay()+7)%7;if(add===0)add=7;d.setUTCDate(d.getUTCDate()+add);return d.toISOString().slice(0,10);}
  async function applyFollowup(raw){
    const q=String(raw||'').trim().toLowerCase();if(!q)return;
    if(/closer|nearer|less travel|shorter drive/.test(q))nextSelect('distance',-1);
    if(/cheaper|lower budget/.test(q))nextSelect('budget',-1);
    if(/\bfree\b/.test(q)){const b=qs('budget');if(b)b.value='0';}
    if(/indoor|inside|rain/.test(q))setChip('indoor');
    if(/outdoor|outside/.test(q))setChip('outdoor');
    if(/ignore weather/.test(q))setChip('any');
    if(/accessible|wheelchair|less walking|mobility/.test(q)){const a=qs('accessible');if(a)a.checked=true;}
    if(/spontaneous|no booking|easy/.test(q)){const s=qs('spontaneous');if(s)s.checked=true;}
    if(/later/.test(q))shiftTime(120);if(/earlier/.test(q))shiftTime(-120);
    if(/tomorrow/.test(q)){const d=qs('date'),x=new Date((d.value||new Date().toISOString().slice(0,10))+'T12:00:00Z');x.setUTCDate(x.getUTCDate()+1);d.value=x.toISOString().slice(0,10);}
    if(/weekend|saturday/.test(q)){const d=qs('date');d.value=nextSaturday(d.value);}
    if(typeof findFamily==='function'){await findFamily(false);const st=qs('status');if(st)st.textContent=`Follow-up applied: “${raw}”. `+st.textContent;}
  }
  function injectFamilyTools(){
    const results=qs('results');if(!results||qs('planTools'))return;
    const node=document.createElement('section');node.id='planTools';node.className='panel';node.innerHTML=`<div class="resultHead"><h2>Keep refining this plan</h2></div><div class="chips"><button class="chip" data-follow="closer">Closer</button><button class="chip" data-follow="cheaper">Cheaper</button><button class="chip" data-follow="indoors">Indoors</button><button class="chip" data-follow="less walking">Less walking</button><button class="chip" data-follow="no booking">No booking</button></div><div class="askbar" style="margin-top:10px"><label class="srOnly" for="followupAsk">Refine your plan</label><input id="followupAsk" placeholder="e.g. closer, cheaper and indoors"><button class="primary" id="followupBtn">Update</button></div><div class="buttons" style="margin-top:12px"><button class="mini go" id="sharePlanBtn">Share plan</button><button class="mini" id="waPlanBtn">WhatsApp</button><button class="mini" id="copyPlanBtn">Copy link</button><button class="mini" id="calendarPlanBtn">Calendar</button></div><p class="desc">“Less walking” currently prioritises results with verified accessibility information; detailed walking-distance data is still being expanded.</p>`;
    results.prepend(node);
    node.querySelectorAll('[data-follow]').forEach(b=>b.onclick=()=>applyFollowup(b.dataset.follow));
    qs('followupBtn').onclick=()=>applyFollowup(qs('followupAsk').value);qs('followupAsk').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();applyFollowup(e.currentTarget.value);}});
    qs('sharePlanBtn').onclick=sharePlan;qs('waPlanBtn').onclick=whatsappPlan;qs('copyPlanBtn').onclick=copyPlanLink;qs('calendarPlanBtn').onclick=calendarPlan;
  }
  function logSearchGap(){
    const box=qs('exploreAsk'),out=qs('exploreResults');if(!box||!out||!box.value.trim())return;
    const count=(typeof EXPLORE_ITEMS!=='undefined'&&Array.isArray(EXPLORE_ITEMS))?EXPLORE_ITEMS.length:out.querySelectorAll('.card,.item').length;
    if(count>2)return;
    let rows=[];try{rows=JSON.parse(localStorage.getItem('askShropshireSearchGaps')||'[]');}catch(e){}
    const row={time:new Date().toISOString(),query:box.value.trim().slice(0,160),area:qs('area')?.value||'',result_count:count};
    if(!rows.some(r=>r.query===row.query&&r.area===row.area&&Date.now()-new Date(r.time).getTime()<86400000))rows.push(row);
    localStorage.setItem('askShropshireSearchGaps',JSON.stringify(rows.slice(-50)));
    if(count===0&&!out.querySelector('.gapHelp'))out.insertAdjacentHTML('beforeend','<div class="card gapHelp"><h3>Couldn’t find it?</h3><p class="desc">Tell Ask Shropshire what was missing so we can improve local coverage.</p><div class="buttons"><a class="mini" href="search-feedback.html">Report a missing result</a></div></div>');
  }
  const exploreObs=qs('exploreResults')&&new MutationObserver(()=>setTimeout(logSearchGap,20));if(exploreObs)exploreObs.observe(qs('exploreResults'),{childList:true,subtree:false});
  async function openSharedPlan(){
    const encoded=new URL(location.href).searchParams.get('plan');if(!encoded)return;
    let p;try{p=unb64url(encoded);}catch(e){return;}
    let tries=0;while((typeof EVENTS==='undefined'||typeof PLACES==='undefined'||(!EVENTS.length&&!PLACES.length))&&tries++<40)await new Promise(r=>setTimeout(r,150));
    if(p.date&&qs('date'))qs('date').value=p.date;if(p.arrival&&qs('arrival'))qs('arrival').value=p.arrival;if(p.area&&qs('area'))qs('area').value=p.area;
    const items=(p.items||[]).map(i=>typeof resolveItem==='function'?resolveItem(i.type,i.id):null).filter(Boolean);
    if(!items.length)return;
    if(typeof routeTable==='function')await routeTable(items);
    const ready=items.map(x=>{const y=typeof attachRoute==='function'?attachRoute(x):x;y.opening=typeof openingState==='function'?openingState(y,p.date||qs('date').value,p.arrival||qs('arrival').value):null;return y;});
    if(typeof LAST_FAMILY!=='undefined')LAST_FAMILY=ready;
    if(typeof showView==='function')showView('family');
    const plans=qs('plans');if(plans&&typeof card==='function')plans.innerHTML=ready.map((x,i)=>card(x,`Shared plan ${String.fromCharCode(65+i)}`,i===1?'alt':i===2?'free':'')).join('');
    const results=qs('results');if(results)results.hidden=false;const more=qs('more');if(more)more.innerHTML='<div class="empty">This shared plan preserves the chosen stops. Use the follow-up box above to recalculate alternatives.</div>';const count=qs('count');if(count)count.textContent=`${ready.length} shared stops`;
  }
  injectFamilyTools();
  window.addEventListener('load',()=>{injectFamilyTools();openSharedPlan();});
})();
