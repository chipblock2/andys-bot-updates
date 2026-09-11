const kind=document.body.dataset.formKind||'form';
const form=document.querySelector('form[data-intake]');
const statusEl=document.getElementById('formStatus');
const key='askShropshireDraft:'+kind;
const FORM_URLS=window.ASK_SHROPSHIRE_INTAKE_ENDPOINTS||{
  event:'https://form.jotform.com/262533659899074',
  business_claim:'https://form.jotform.com/262533549106053',
  alerts:'https://form.jotform.com/262533678449066',
  offer:'https://form.jotform.com/262534146466056',
  business_update:null
};
function setStatus(msg){if(statusEl)statusEl.textContent=msg;}
function readForm(){const data={};if(!form)return data;new FormData(form).forEach((v,k)=>{if(data[k])data[k]=[].concat(data[k],v);else data[k]=v});return data;}
function saveDraft(){if(!form)return;localStorage.setItem(key,JSON.stringify({saved_at:new Date().toISOString(),data:readForm()}));setStatus('Draft saved on this device only. It has not been submitted.');}
function restoreDraft(){if(!form)return;try{const saved=JSON.parse(localStorage.getItem(key)||'null');if(!saved?.data)return;for(const [k,v] of Object.entries(saved.data)){const nodes=form.querySelectorAll(`[name="${CSS.escape(k)}"]`);nodes.forEach(n=>{if(n.type==='checkbox')n.checked=Array.isArray(v)?v.includes(n.value):v===n.value||v==='on';else if(n.type==='radio')n.checked=n.value===v;else n.value=Array.isArray(v)?v[0]:v;});}setStatus(FORM_URLS[kind]?'A saved draft was restored. When ready, continue to the secure submission form.':'A saved draft was restored. Secure submission for this form is not connected yet.');}catch(e){}}
form?.addEventListener('submit',e=>{e.preventDefault();if(!form.reportValidity())return;saveDraft();const url=FORM_URLS[kind];if(!url){setStatus('Secure submission for this form is not connected yet. Your draft remains saved on this device.');return;}setStatus('Opening the secure Ask Shropshire submission form…');window.location.href=url;});
document.getElementById('saveDraft')?.addEventListener('click',saveDraft);
document.getElementById('clearDraft')?.addEventListener('click',()=>{localStorage.removeItem(key);form?.reset();setStatus('Draft cleared.');});
restoreDraft();
if(statusEl&&!localStorage.getItem(key))setStatus(FORM_URLS[kind]?'Your submission is completed securely through Ask Shropshire’s Jotform intake and reviewed before any public change.':'Secure submission for this form is not connected yet. You can still save a draft on this device.');