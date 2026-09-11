const kind=document.body.dataset.formKind||'form';
const form=document.querySelector('form[data-intake]');
const statusEl=document.getElementById('formStatus');
const key='askShropshireDraft:'+kind;
function setStatus(msg){if(statusEl)statusEl.textContent=msg;}
function readForm(){const data={};if(!form)return data;new FormData(form).forEach((v,k)=>{if(data[k])data[k]=[].concat(data[k],v);else data[k]=v});return data;}
function saveDraft(){if(!form)return;localStorage.setItem(key,JSON.stringify({saved_at:new Date().toISOString(),data:readForm()}));setStatus('Draft saved on this device only. It has not been submitted.');}
function restoreDraft(){if(!form)return;try{const saved=JSON.parse(localStorage.getItem(key)||'null');if(!saved?.data)return;for(const [k,v] of Object.entries(saved.data)){const nodes=form.querySelectorAll(`[name="${CSS.escape(k)}"]`);nodes.forEach(n=>{if(n.type==='checkbox')n.checked=Array.isArray(v)?v.includes(n.value):v===n.value||v==='on';else if(n.type==='radio')n.checked=n.value===v;else n.value=Array.isArray(v)?v[0]:v;});}setStatus('A saved draft was restored from this device.');}catch(e){}}
form?.addEventListener('submit',e=>{e.preventDefault();saveDraft();setStatus('Secure public submission is not connected yet. Connect the Jotform intake before launch; this draft remains on this device only.');});
document.getElementById('saveDraft')?.addEventListener('click',saveDraft);
document.getElementById('clearDraft')?.addEventListener('click',()=>{localStorage.removeItem(key);form?.reset();setStatus('Draft cleared.');});
restoreDraft();