#!/usr/bin/env python3
"""R7.5 live-position exit advisor (shadow only).

Reads live positions and public Coinbase candles. Recommends a tighter stop using
fee-aware break-even + ATR trailing logic. It NEVER edits/cancels/submits orders.
"""
from __future__ import annotations
import json,time,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from exit_policy import recommend_stop

ROOT=Path(__file__).resolve().parent
STATUS=ROOT/"state"/"exit_advisor_status.json"
AUDIT=ROOT/"state"/"exit_advisor_audit.jsonl"
URL="http://127.0.0.1:8787/api/live"
API="https://api.exchange.coinbase.com"
CFG={"expected_slippage_bps":10,"break_even_trigger_r":1.0,"trail_trigger_r":1.5,"trail_atr_mult":2.5,"stop_price_buffer_bps":5}
try:
    CFG.update(json.loads((ROOT/"config.json").read_text(encoding="utf-8")))
except Exception:
    pass

def iso(t):
    return datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def live():
    req=urllib.request.Request(URL,headers={"User-Agent":"AndysBot-R75-ExitAdvisor"})
    with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)

def candles(product,start,end):
    rows=[]; gran=300; t=max(start,end-300*gran)
    q=urllib.parse.urlencode({"granularity":gran,"start":iso(t),"end":iso(end)})
    req=urllib.request.Request(f"{API}/products/{product}/candles?{q}",headers={"User-Agent":"AndysBot-R75-ExitAdvisor"})
    with urllib.request.urlopen(req,timeout=12) as r:data=json.load(r)
    if isinstance(data,list):
        rows=[x for x in data if isinstance(x,list) and len(x)>=6]
    return rows

def save(path,obj):
    raw=json.dumps(obj,indent=2)
    try:
        tmp=path.with_suffix(".tmp");tmp.write_text(raw,encoding="utf-8");tmp.replace(path)
    except PermissionError:
        path.write_text(raw,encoding="utf-8");json.loads(path.read_text(encoding="utf-8"))
def once():
    d=live();lc=d.get("live_canary") or {};assets=d.get("assets") or {}
    fee=d.get("fee_profile") or {}
    maker=float(fee.get("maker_fee") or .0006);taker=float(fee.get("taker_fee") or .0016)
    now=time.time();rows=[]
    for sym,pos in (lc.get("positions") or {}).items():
        product=str(pos.get("product_id") or f"{sym}-GBP")
        entry=float(pos.get("entry_price") or 0);stop=float(pos.get("stop_price") or 0)
        initial_stop=float(pos.get("model_stop_price") or stop)
        opened=float(pos.get("opened_ts") or now)
        a=assets.get(sym) or {}
        current=float(a.get("coinbase_price") or a.get("price") or entry)
        atr_pct=float(a.get("atr_pct") or 0)
        atr_abs=current*atr_pct
        try:
            cs=candles(product,opened,now)
            highest=max([float(x[2]) for x in cs],default=current)
        except Exception:
            highest=current
        rec=recommend_stop(entry=entry,current=current,highest=highest,atr=atr_abs,
                           current_stop=stop,initial_stop=initial_stop,
                           maker_fee=maker,taker_fee=taker,config=CFG)
        lock_pct=(float(rec.get("stop") or stop)/entry-1)*100 if entry else 0
        rows.append({
            "symbol":sym,"product":product,"entry":entry,"current":current,
            "highest_since_entry":highest,"atr_abs":atr_abs,
            "exchange_stop":stop,"exchange_target":float(pos.get("target_price") or 0),
            "protection_status":pos.get("protection_status"),
            "recommendation":rec,"locked_gain_pct_at_recommended_stop":round(lock_pct,3),
            "can_edit_orders":False,
        })
    out={"schema":"andys-bot-r7.5-exit-advisor-v1","generated_utc":iso(now),
         "shadow_only":True,"can_edit_orders":False,"positions":rows}
    STATUS.parent.mkdir(parents=True,exist_ok=True);save(STATUS,out)
    with AUDIT.open("a",encoding="utf-8") as f:
        f.write(json.dumps({"utc":out["generated_utc"],"recommendations":[{"symbol":x["symbol"],"action":x["recommendation"].get("action"),"stop":x["recommendation"].get("stop")} for x in rows]})+"\n")
    return out

def main():
    print("R7.5 EXIT ADVISOR - SHADOW ONLY",flush=True)
    while True:
        try: print(once(),flush=True)
        except Exception as e: print("ERROR",repr(e),flush=True)
        time.sleep(60)

if __name__=="__main__":main()