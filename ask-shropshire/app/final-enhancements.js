(()=>{
  const $=id=>document.getElementById(id);

  function choosePlans(){
    const c=(typeof LAST_FAMILY!=='undefined'&&Array.isArray(LAST_FAMILY))?LAST_FAMILY:[];
    if(!c.length)return[];
    const A=c[0];
    const indoor=x=>/indoor/i.test(String(x.indoor_outdoor||''));
    const mixed=x=>/mixed/i.test(String(x.indoor_outdoor||''));
    const free=x=>x.price_from===0||x.price_level==='Free'||(x.price_from!=null&&Number(x.price_from)<=10);
    const easy=x=>x.same_day_friendly&&!x.booking_required;
    let B=c.find(x=>x.id!==A.id&&x.type!==A.type&&indoor(x))
      ||c.find(x=>x.id!==A.id&&indoor(x))
      ||c.find(x=>x.id!==A.id&&x.type!==A.type&&mixed(x))
      ||c.find(x=>x.id!==A.id&&x.type!==A.type)
      ||c.find(x=>x.id!==A.id);
    let C=c.find(x=>x.id!==A.id&&x.id!==B?.id&&free(x)&&easy(x))
      ||c.find(x=>x.id!==A.id&&x.id!==B?.id&&free(x))
      ||c.find(x=>x.id!==A.id&&x.id!==B?.id&&easy(x))
      ||c.find(x=>x.id!==A.id&&x.id!==B?.id);
    return [A,B,C].filter(Boolean);
  }

  function rerenderDiversePlans(){
    if(typeof card!=='function'||!$('plans'))return;
    const p=choosePlans();
    if(!p.length)return;
    $('plans').innerHTML=p.map((x,i)=>card(x,i===0?'Plan A · best match':i===1?'Plan B · practical backup':'Plan C · cheaper / flexible',i===1?'alt':i===2?'free':'')).join('');
  }

  if(typeof findFamily==='function'){
    const original=findFamily;
    findFamily=async function(scroll=true){const r=await original(scroll);rerenderDiversePlans();return r;};
  }

  function addFeedbackLink(){
    const more=document.querySelector('#moreView .cards');
    if(more&&!document.getElementById('coverageFeedbackCard')){
      more.insertAdjacentHTML('beforeend',`<div class="card" id="coverageFeedbackCard"><h3>Help improve Ask Shropshire</h3><p class="desc">Couldn’t find something local? Tell us what was missing so the discovery system knows what coverage to improve next.</p><div class="buttons"><a class="mini" href="search-feedback.html">Report a missing result</a></div></div>`);
    }
  }

  function restoreSharedFallback(){
    const params=new URL(location.href).searchParams,encoded=params.get('plan');
    if(!encoded)return;
    setTimeout(()=>{
      const results=$('results'),plans=$('plans');
      if(!results||!plans||!results.hidden)return;
      try{
        const pad=encoded.replace(/-/g,'+').replace(/_/g,'/');
        const bin=atob(pad+'==='.slice((pad.length+3)%4));
        const bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));
        const p=JSON.parse(new TextDecoder().decode(bytes));
        if(!Array.isArray(p.items)||!p.items.length)return;
        if(typeof showView==='function')showView('family');
        plans.innerHTML=p.items.map((x,i)=>`<article class="plan ${i===1?'alt':i===2?'free':''}"><div class="planLabel">Shared plan ${String.fromCharCode(65+i)}</div><h3>${String(x.name||'Saved stop').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}</h3><p class="meta">${String(x.town||'Shropshire').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}</p><p class="desc">This stop is no longer available in the current live feed. Re-run the Family Day Finder for a current alternative.</p></article>`).join('');
        results.hidden=false;if($('count'))$('count').textContent=`${p.items.length} shared stops`;if($('more'))$('more').innerHTML='<div class="empty">Some shared stops may have changed since this link was created. Recalculate for current availability.</div>';
      }catch(e){}
    },1500);
  }

  addFeedbackLink();
  window.addEventListener('load',()=>{addFeedbackLink();restoreSharedFallback();});
})();
