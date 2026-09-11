const CACHE='ask-shropshire-v10';
const APP_SHELL=['./','./index.html','./app.css','./app.js','./pwa.js','./features.js','./final-enhancements.js','./feed-patch.js','./manifest.webmanifest','./privacy.html','./accessibility.html','./submit-event.html','./claim-business.html','./update-business.html','./alerts.html','./deals.html','./submit-offer.html','./search-feedback.html','./intake.js','./intake-config.js','./deals.js','./icon.svg','./maskable.svg','./icon-192.png','./icon-512.png'];
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
  if(['raw.githubusercontent.com','api.open-meteo.com','router.project-osrm.org','unpkg.com'].includes(url.hostname)||url.hostname.endsWith('tile.openstreetmap.org')){
    event.respondWith(fetch(req).then(res=>{const clone=res.clone();caches.open(CACHE).then(c=>c.put(req,clone)).catch(()=>{});return res}).catch(()=>caches.match(req)));
  }
});
self.addEventListener('message',event=>{if(event.data==='SKIP_WAITING')self.skipWaiting()});