let deferredInstallPrompt=null;
const installBtn=document.getElementById('installBtn');
function routeFromHash(){const name=(location.hash||'').replace('#','').toLowerCase();if(['home','explore','family','saved','more'].includes(name)){const nav=document.querySelector(`.nav[data-view="${name}"]`);if(nav)nav.click();}}
window.addEventListener('hashchange',routeFromHash);
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();deferredInstallPrompt=event;if(installBtn)installBtn.hidden=false;});
if(installBtn){installBtn.addEventListener('click',async()=>{if(!deferredInstallPrompt)return;deferredInstallPrompt.prompt();await deferredInstallPrompt.userChoice;deferredInstallPrompt=null;installBtn.hidden=true;});}
window.addEventListener('appinstalled',()=>{deferredInstallPrompt=null;if(installBtn)installBtn.hidden=true;});
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
