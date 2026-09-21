#!/usr/bin/env python3
"""R7.5 exit counterfactual learner (shadow only).

Tracks the tighter stop recommended by exit_advisor.py. If price later crosses
that shadow stop, records the hypothetical exit at live best bid. When Coinbase
actually closes the position, compares shadow P/L with actual realised P/L.
Never edits, cancels, previews or submits an order.
"""
from __future__ import annotations
import csv,json,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATE=ROOT/"state"/"exit_counterfactual_state.json"
STATUS=ROOT/"state"/"exit_counterfactual_status.json"
CSV=ROOT/"exit_counterfactual.csv"
ADVISOR=ROOT/"state"/"exit_advisor_status.json"
URL="http://127.0.0.1:8787/api/live"
API="https://api.exchange.coinbase.com"

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

def save(path,obj):
    raw=json.dumps(obj,indent=2)
    try:
        tmp=path.with_suffix(".tmp");tmp.write_text(raw,encoding="utf-8");tmp.replace(path)
    except PermissionError:
        path.write_text(raw,encoding="utf-8");json.loads(path.read_text(encoding="utf-8"))

def live():
    req=urllib.request.Request(URL,headers={"User-Agent":"AndysBot-R75-ExitCounterfactual"})
    with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)

def ticker(product):
    req=urllib.request.Request(f"{API}/products/{product}/ticker",headers={"User-Agent":"AndysBot-R75-ExitCounterfactual"})
    with urllib.request.urlopen(req,timeout=8) as r:
        d=json.load(r)
    return {"price":float(d.get("price") or 0),"bid":float(d.get("bid") or 0),"ask":float(d.get("ask") or 0)}

def append(row):
    new=not CSV.exists()
    with CSV.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(row))
        if new:w.writeheader()
        w.writerow(row)
def once():
    d=live();lc=d.get("live_canary") or {};assets=d.get("assets") or {}
    adv=load(ADVISOR,{});adv_by={x.get("symbol"):x for x in adv.get("positions",[]) if isinstance(x,dict)}
    fee=float((d.get("fee_profile") or {}).get("taker_fee") or .0016)
    st=load(STATE,{"episodes":{},"closed":0,"shadow_triggered":0,"shadow_better":0,"delta_sum_gbp":0.0})
    eps=st.setdefault("episodes",{});now=time.time()
    current=set()
    winners={str(x.get("symbol")):x for x in (lc.get("winner_watch") or []) if isinstance(x,dict)}

    for sym,pos in (lc.get("positions") or {}).items():
        current.add(sym);a=assets.get(sym) or {};book=a.get("coinbase_orderbook") or {}
        product=str(pos.get("product_id") or f"{sym}-GBP")
        fallback_current=float((winners.get(sym) or {}).get("price") or a.get("coinbase_price") or a.get("price") or pos.get("entry_price") or 0)
        try:
            tk=ticker(product);current_px=float(tk.get("price") or fallback_current);bid=float(tk.get("bid") or current_px)
        except Exception:
            current_px=fallback_current;bid=float(book.get("best_bid") or current_px)
        recommendation=((adv_by.get(sym) or {}).get("recommendation") or {})
        rec_stop=float(recommendation.get("stop") or pos.get("stop_price") or 0)
        e=eps.get(sym)
        if not e:
            e={
                "symbol":sym,"opened":now,"position_opened_ts":float(pos.get("opened_ts") or now),
                "entry":float(pos.get("entry_price") or 0),"entry_cost_gbp":float(pos.get("entry_cost_gbp") or 0),
                "qty":float(pos.get("filled_size") or 0),"original_exchange_stop":float(pos.get("stop_price") or 0),
                "target":float(pos.get("target_price") or 0),"max_shadow_stop":rec_stop,
                "shadow_triggered":False,"shadow_exit_price":None,"shadow_pnl_gbp":None,
            };eps[sym]=e
        e["max_shadow_stop"]=max(float(e.get("max_shadow_stop") or 0),rec_stop)
        if not e.get("shadow_triggered") and bid>0 and e["max_shadow_stop"]>0 and bid<=e["max_shadow_stop"]:
            proceeds=float(e["qty"])*bid*(1-fee)
            pnl=proceeds-float(e["entry_cost_gbp"])
            e.update({"shadow_triggered":True,"shadow_trigger_ts":now,"shadow_exit_price":bid,"shadow_pnl_gbp":pnl})
            st["shadow_triggered"]=int(st.get("shadow_triggered",0))+1

    for sym,e in list(eps.items()):
        if sym in current:continue
        last=lc.get("last_exit") or {}
        actual_pnl=float(last.get("pnl_gbp") or 0) if str(last.get("symbol") or "")==sym else 0.0
        actual_exit=float(last.get("exit_price") or 0) if str(last.get("symbol") or "")==sym else 0.0
        actual_kind=str(last.get("exit_kind") or "UNKNOWN") if str(last.get("symbol") or "")==sym else "UNKNOWN"
        shadow_pnl=float(e.get("shadow_pnl_gbp")) if e.get("shadow_triggered") else actual_pnl
        delta=shadow_pnl-actual_pnl
        row={
            "symbol":sym,"entry":e.get("entry"),"original_exchange_stop":e.get("original_exchange_stop"),
            "highest_shadow_stop":e.get("max_shadow_stop"),"shadow_triggered":bool(e.get("shadow_triggered")),
            "shadow_exit_price":e.get("shadow_exit_price"),"shadow_pnl_gbp":round(shadow_pnl,6),
            "actual_exit_price":actual_exit,"actual_exit_kind":actual_kind,"actual_pnl_gbp":round(actual_pnl,6),
            "shadow_minus_actual_gbp":round(delta,6),
        }
        append(row);st["closed"]=int(st.get("closed",0))+1
        if delta>0:st["shadow_better"]=int(st.get("shadow_better",0))+1
        st["delta_sum_gbp"]=float(st.get("delta_sum_gbp",0))+delta
        eps.pop(sym,None)

    save(STATE,st);closed=int(st.get("closed",0))
    out={
        "schema":"andys-bot-r7.5-exit-counterfactual-v1",
        "generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(now)),
        "shadow_only":True,"can_edit_orders":False,
        "open_episodes":len(eps),"closed":closed,
        "shadow_triggered":int(st.get("shadow_triggered",0)),
        "shadow_better":int(st.get("shadow_better",0)),
        "shadow_better_rate":(int(st.get("shadow_better",0))/closed if closed else None),
        "avg_shadow_minus_actual_gbp":(float(st.get("delta_sum_gbp",0))/closed if closed else None),
    }
    save(STATUS,out);return out

def main():
    print("R7.5 EXIT COUNTERFACTUAL - SHADOW ONLY",flush=True)
    while True:
        try:print(once(),flush=True)
        except Exception as e:print("ERROR",repr(e),flush=True)
        time.sleep(5)

if __name__=="__main__":main()