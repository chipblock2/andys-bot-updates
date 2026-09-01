#!/usr/bin/env python3
"""Andy's Bot R7.3 Agentic Companion — read-only/shadow supervisor.
Consumes the existing local /api/live state. It never calls live preview, approval,
order, transfer or risk-change endpoints.
"""
from __future__ import annotations
import json, math, os, threading, time, urllib.request, webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parent; STATE=ROOT/'state'; CFG=ROOT/'config.json'
STATUS=STATE/'agentic_status.json'; AUDIT=STATE/'agentic_audit.jsonl'
DEFAULT={"mode":"SHADOW_ONLY","scan_seconds":300,"deep_scan_seconds":3600,"agent_min_score":78,"watch_min_score":65,"max_positions_hard":8,"max_order_gbp_hard":10.0,"max_exposure_gbp_hard":20.0,"allow_live_orders":False,"allow_transfers":False,"allow_risk_changes":False,"dashboard_host":"127.0.0.1","dashboard_port":8793,"bot_urls":["http://127.0.0.1:8765","http://127.0.0.1:8787","http://127.0.0.1:8000","http://127.0.0.1:8080","http://127.0.0.1:5000","http://127.0.0.1:5001","http://127.0.0.1:8888","http://127.0.0.1:3000"]}

def n(v,d=0.0):
    try:
        x=float(v); return x if math.isfinite(x) else d
    except Exception:return d

def cl(v,a=0,b=100):return max(a,min(b,v))
def iso():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def config():
    c=dict(DEFAULT)
    try:c.update(json.loads(CFG.read_text(encoding='utf-8')))
    except Exception:pass
    c['mode']='SHADOW_ONLY'; c['allow_live_orders']=c['allow_transfers']=c['allow_risk_changes']=False
    c['max_positions_hard']=min(8,int(n(c.get('max_positions_hard'),8)))
    c['max_order_gbp_hard']=min(10.0,n(c.get('max_order_gbp_hard'),10))
    c['max_exposure_gbp_hard']=min(20.0,n(c.get('max_exposure_gbp_hard'),20))
    return c

def get_json(url):
    q=urllib.request.Request(url,headers={'User-Agent':'AndysBot-R7.3-Agentic/1.0'})
    with urllib.request.urlopen(q,timeout=1.5) as r:return json.loads(r.read().decode())

def snapshot(c):
    urls=[]; e=os.getenv('ANDYS_BOT_URL','').strip().rstrip('/')
    if e:urls.append(e)
    urls += [str(x).rstrip('/') for x in c.get('bot_urls',[])]
    errs=[]
    for u in dict.fromkeys(urls):
        try:
            d=get_json(u+'/api/live')
            if isinstance(d,dict) and ('assets' in d or 'live_canary' in d):return u,d
        except Exception as x:errs.append(f'{u}: {x}')
    raise RuntimeError('No local Andy\'s Bot API found. '+' | '.join(errs[-3:]))

def score(sym,a,s):
    dc=a.get('decision_council') or {}; cal=a.get('confidence_calibration') or {}; mt=a.get('multi_timeframe') or {}; op=a.get('market_opportunity') or {}; ep=a.get('edge_profile') or {}; nw=a.get('news_social') or {}; ox=a.get('okx_intelligence') or {}; mq=a.get('market_quality') or {}
    raw=n(a.get('ensemble_probability'),.5); p=n(a.get('calibrated_probability'),n(cal.get('calibrated_probability'),raw)); exp=n(a.get('expected_return')); req=n(a.get('required_edge')); mult=exp/req if req>0 else 0
    em=0 if mult<=0 else (100 if mult>=2 else cl((mult-.55)/1.45*100))
    comp={'council':cl(n(dc.get('score'),50)),'prob':cl(p*100),'edge':em,'mtf':cl(50+n(mt.get('score'))*.5),'activity':cl(n(op.get('activity_score'),50)),'coin_edge':cl(n(ep.get('edge_score'),50)),'news':cl(50+n(nw.get('score'))*.5),'perp':cl(50+n(ox.get('score'))*.5),'quality':cl(n(mq.get('score'),60))}
    w={'council':.23,'prob':.15,'edge':.20,'mtf':.10,'activity':.09,'coin_edge':.08,'news':.04,'perp':.05,'quality':.06}; total=sum(comp[k]*w[k] for k in w)
    blockers=[]; cautions=[]; positives=[]; action=str(a.get('action') or 'HOLD').upper()
    if req>0 and exp<req:blockers.append('expected move does not clear cost gate')
    if op.get('chase_risk'):blockers.append('chase/extension risk'); total-=14
    if action not in {'BUY','LONG','TRADE'}:cautions.append('base engine action '+action); total-=6
    if comp['quality']<45:blockers.append('market quality too weak')
    if comp['council']>=75:positives.append('Decision Council strong')
    if mult>=1.35:positives.append(f'edge clears costs by {mult:.2f}x')
    if comp['mtf']>=65:positives.append('multi-timeframe supportive')
    if comp['perp']>=62:positives.append('read-only perp context supportive')
    ctx=s.get('btc_regime_breadth') or {}; btc=str((ctx.get('btc') or {}).get('state') or '').upper(); breadth=str((ctx.get('breadth') or {}).get('state') or '').upper()
    if btc in {'BREAKDOWN','CRASH','BEARISH_BREAKDOWN'}:cautions.append('BTC regime defensive'); total-=10
    if breadth in {'WEAK','NARROW'}:cautions.append('alt breadth weak'); total-=7
    return {'symbol':sym,'score':round(cl(total),1),'base_action':action,'calibrated_probability':round(p,4),'expected_return':round(exp,6),'required_edge':round(req,6),'edge_multiple':round(mult,2),'components':{k:round(v,1) for k,v in comp.items()},'blockers':blockers,'cautions':cautions,'positives':positives,'reason':a.get('reason') or ''}

def analyse(s,c,deep=False):
    rows=sorted([score(str(k),v or {},s) for k,v in (s.get('assets') or {}).items() if isinstance(v,dict)],key=lambda x:x['score'],reverse=True)
    lc=s.get('live_canary') or {}; pos=lc.get('positions') or {}; pos=pos if isinstance(pos,dict) else {}; botmax=int(n(lc.get('max_positions'),8)); mx=min(8,botmax if botmax>0 else 8); open_=len(pos); exposure=n(lc.get('exposure_gbp')); maxexp=min(20,n(lc.get('max_exposure_gbp'),20)); best=rows[0] if rows else None
    decision='NO_TRADE'; reason='No candidate clears the Agentic quality threshold.'
    if best:
        if open_>=mx:decision='PORTFOLIO_FULL_REVIEW_ONLY'; reason='All live slots are occupied; no ninth position will be forced.'
        elif exposure>=maxexp-1e-9:decision='EXPOSURE_FULL_REVIEW_ONLY'; reason='Exposure cap is full; no new trade recommendation.'
        elif best['score']>=n(c.get('agent_min_score'),78) and not best['blockers'] and best['base_action'] in {'BUY','LONG','TRADE'}:decision='SHADOW_TRADE_READY'; reason=f"{best['symbol']} clears Agentic quality; existing bot still controls preview/approval."
        elif best['score']>=n(c.get('watch_min_score'),65):decision='WATCH'; reason=f"{best['symbol']} is interesting but not trade-ready."
    by={x['symbol']:x for x in rows}; reviews=[]
    for sym in pos:
        k=str(sym).replace('-GBP',''); sc=(by.get(k) or {}).get('score',50); stance='REVIEW_EXIT' if sc<42 else ('PROTECT' if sc<58 else 'HOLD'); reviews.append({'symbol':k,'stance':stance,'current_score':sc,'note':'Advice only; companion cannot execute.'})
    return {'schema':'andys-bot-agentic-status-v1','generated_utc':iso(),'mode':'SHADOW_ONLY','deep_review':deep,'decision':decision,'decision_reason':reason,'best_candidate':best,'top_candidates':rows[:10],'portfolio':{'open_positions':open_,'max_positions':mx,'slots_free':max(0,mx-open_),'exposure_gbp':round(exposure,2),'max_exposure_gbp':round(maxexp,2),'hard_order_cap_gbp':10.0},'position_reviews':reviews,'guardrails':{'live_orders':False,'transfers':False,'risk_changes':False,'max_positions_hard':8,'max_order_gbp_hard':10.0,'max_exposure_gbp_hard':20.0}}

class Engine:
    def __init__(self,c):self.c=c;self.lock=threading.RLock();self.kick=threading.Event();self.stop=threading.Event();self.lastdeep=0;self.status={'generated_utc':iso(),'mode':'SHADOW_ONLY','decision':'STARTING','decision_reason':'Looking for local bot API.'};STATE.mkdir(parents=True,exist_ok=True)
    def save(self):STATUS.write_text(json.dumps(self.status,indent=2),encoding='utf-8')
    def log(self,x):
        x={'utc':iso(),**x}
        with AUDIT.open('a',encoding='utf-8') as f:f.write(json.dumps(x,separators=(',',':'))+'\n')
    def scan(self,deep=False):
        now=time.time(); deep=deep or not self.lastdeep or now-self.lastdeep>=n(self.c.get('deep_scan_seconds'),3600)
        try:
            u,s=snapshot(self.c); d=analyse(s,self.c,deep); d.update({'bot_url':u,'api_health':'CONNECTED','last_scan_utc':iso()}); self.status=d
            if deep:self.lastdeep=now
            self.log({'type':'deep_review' if deep else 'market_scan','decision':d['decision'],'best':(d.get('best_candidate') or {}).get('symbol'),'score':(d.get('best_candidate') or {}).get('score')})
        except Exception as x:self.status={**self.status,'generated_utc':iso(),'decision':'BOT_API_OFFLINE','decision_reason':str(x),'api_health':'OFFLINE'};self.log({'type':'api_error','error':str(x)})
        self.save()
    def loop(self):
        self.scan(True)
        while not self.stop.is_set():self.kick.wait(max(30,int(n(self.c.get('scan_seconds'),300))));self.kick.clear();self.scan(False)

HTML='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Andy’s Bot R7.3 Agentic</title><style>body{background:#071019;color:#eef6fb;font:14px Segoe UI;padding:18px}main{max-width:1100px;margin:auto}.card{background:#0d1c28;border:1px solid #27445a;border-radius:14px;padding:14px;margin:10px 0}.g{color:#45e69b}.a{color:#ffc75b}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #20384a;text-align:left}button{padding:9px 12px;background:#17344a;color:white;border:1px solid #38617e;border-radius:9px}</style><main><h1>Andy’s Bot R7.3 — Agentic Companion</h1><p class="g"><b>SHADOW ONLY</b> • no live orders • no transfers • no risk changes</p><button onclick="fetch('/scan',{method:'POST'})">Scan now</button><div class="card"><h2 id="d">STARTING</h2><div id="w"></div></div><div class="card"><b id="p">Portfolio</b></div><div class="card"><table><thead><tr><th>Coin</th><th>Score</th><th>Base</th><th>Edge</th><th>Blockers</th></tr></thead><tbody id="r"></tbody></table></div><script>async function L(){let x=await fetch('/status').then(r=>r.json());d.textContent=x.decision;w.textContent=x.decision_reason;let q=x.portfolio||{};p.textContent=`${q.open_positions||0}/${q.max_positions||8} positions • £${Number(q.exposure_gbp||0).toFixed(2)}/£${Number(q.max_exposure_gbp||20).toFixed(2)} exposure`;r.innerHTML=(x.top_candidates||[]).map(z=>`<tr><td>${z.symbol}</td><td>${z.score}</td><td>${z.base_action}</td><td>${z.edge_multiple}x</td><td>${(z.blockers||[]).join(' • ')||'—'}</td></tr>`).join('')}L();setInterval(L,5000)</script></main>'''
class H(BaseHTTPRequestHandler):
    engine=None
    def send(self,code,ct,b):self.send_response(code);self.send_header('Content-Type',ct);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path=='/':self.send(200,'text/html; charset=utf-8',HTML.encode())
        elif self.path=='/status':self.send(200,'application/json',json.dumps(self.engine.status,indent=2).encode())
        elif self.path=='/health':self.send(200,'application/json',json.dumps({'ok':True,'mode':'SHADOW_ONLY','api_health':self.engine.status.get('api_health')}).encode())
        else:self.send(404,'text/plain',b'Not found')
    def do_POST(self):
        if self.path=='/scan':self.engine.kick.set();self.send(202,'application/json',b'{"queued":true}')
        else:self.send(404,'application/json',b'{}')
    def log_message(self,*a):pass

def main():
    c=config(); e=Engine(c); H.engine=e; threading.Thread(target=e.loop,daemon=True).start(); host=c.get('dashboard_host','127.0.0.1');port=int(n(c.get('dashboard_port'),8793));srv=ThreadingHTTPServer((host,port),H);url=f'http://{host}:{port}/';print("Andy's Bot R7.3 Agentic Companion — SHADOW_ONLY");print(url);threading.Timer(.8,lambda:webbrowser.open(url)).start()
    try:srv.serve_forever(.5)
    except KeyboardInterrupt:pass
    finally:e.stop.set();e.kick.set();srv.server_close()
if __name__=='__main__':main()
