const CACHE='ask-shropshire-v1';
const APP_SHELL=['./','./index.html','./app.css','./app.js','./manifest.webmanifest','./privacy.html','./accessibility.html','./icon.svg','./maskable.svg'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(APP_SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',event=>{
  const req=event.request;
  if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin===location.origin){
    event.respondWith(fetch(req).then(res=>{const clone=res.clone();caches.open(CACHE).then(c=>c.put(req,clone));return res}).catch(()=>caches.match(req).then(r=>r||caches.match('./index.html'))));
    return;
  }
  if(url.hostname==='raw.githubusercontent.com'||url.hostname==='api.open-meteo.com'||url.hostname==='router.project-osrm.org'){
    event.respondWith(fetch(req).then(res=>{const clone=res.clone();caches.open(CACHE).then(c=>c.put(req,clone));return res}).catch(()=>caches.match(req)));
  }
});
self.addEventListener('message',event=>{if(event.data==='SKIP_WAITING')self.skipWaiting()});