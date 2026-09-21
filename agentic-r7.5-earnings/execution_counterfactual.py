#!/usr/bin/env python3
"""R7.5 counterfactual execution learner.

Observes the local /api/live feed and R7.5 shadow decisions. It NEVER places,
previews, cancels or edits an order. It compares:
  A) immediate taker buy at the observed ask
  B) hypothetical maker buy at the observed bid if the market later trades/touches it
then marks both to the future bid after a fixed horizon.
"""
from __future__ import annotations
import csv,json,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATE=ROOT/"state"/"execution_counterfactual_state.json"
CSV=ROOT/"execution_counterfactual.csv"
STATUS=ROOT/"state"/"execution_counterfactual_status.json"
R75=ROOT/"state"/"r7_5_live_shadow_status.json"
URL="http://127.0.0.1:8787/api/live"
POLL=5
MAKER_TTL=60
HORIZON=900

def load(p,default):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return default

def save(p,obj):
    raw=json.dumps(obj,indent=2)
    try:
        tmp=p.with_suffix(".tmp");tmp.write_text(raw,encoding="utf-8");tmp.replace(p)
    except PermissionError:
        p.write_text(raw,encoding="utf-8");json.loads(p.read_text(encoding="utf-8"))

def live():
    req=urllib.request.Request(URL,headers={"User-Agent":"AndysBot-R75-Counterfactual"})
    with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)

def candidate_map():
    s=load(R75,{})
    return {str(x.get("product")):x for x in s.get("candidates",[]) if isinstance(x,dict)}

def fee_rates(d):
    f=d.get("fee_profile") or {}
    return float(f.get("maker_fee") or .0006),float(f.get("taker_fee") or .0016)

def book(a):
    b=a.get("coinbase_orderbook") or {}
    return float(b.get("best_bid") or 0),float(b.get("best_ask") or 0)

def append(row):
    new=not CSV.exists()
    with CSV.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(row))
        if new:w.writeheader()
        w.writerow(row)
def step():
    d=live(); cm=candidate_map(); now=time.time(); maker,taker=fee_rates(d)
    st=load(STATE,{"episodes":{},"closed":0,"maker_fills":0,"maker_sum":0.0,"taker_sum":0.0})
    eps=st.setdefault("episodes",{})
    assets=d.get("assets") or {}

    for product,c in cm.items():
        sym=product.split("-")[0]; a=assets.get(sym) or {}
        bid,ask=book(a)
        if bid<=0 or ask<=0:continue
        # Learn from trade-worthy evidence even when the base engine vetoes it.
        learnable=(
            str((c.get("health") or {}).get("state"))=="READY"
            and bool((c.get("edge") or {}).get("allowed"))
            and bool((c.get("liquidity") or {}).get("allowed"))
        )
        key=f"{product}:{int(now//60)}"
        if learnable and key not in eps:
            eps[key]={
                "product":product,"symbol":sym,"opened":now,
                "bid":bid,"ask":ask,"maker_fee":maker,"taker_fee":taker,
                "expected_return":float((c.get("edge") or {}).get("expected_return") or 0),
                "candidate_state":c.get("state"),
                "route":((c.get("smart_execution") or {}).get("route")),
                "maker_filled":False,"maker_fill_ts":None,
            }

    closed=[]
    for key,e in list(eps.items()):
        a=assets.get(e["symbol"]) or {}; bid,ask=book(a)
        if bid<=0 or ask<=0:continue
        age=now-float(e["opened"])
        if not e.get("maker_filled") and age<=MAKER_TTL and ask<=float(e["bid"]):
            e["maker_filled"]=True;e["maker_fill_ts"]=now
        if age>=HORIZON:
            exit_bid=bid
            taker_ret=(exit_bid/float(e["ask"])-1)-float(e["taker_fee"])*2
            if e.get("maker_filled"):
                maker_ret=(exit_bid/float(e["bid"])-1)-float(e["maker_fee"])-float(e["taker_fee"])
            else:
                maker_ret=0.0
            row={
                "opened_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(float(e["opened"]))),
                "closed_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(now)),
                "product":e["product"],"initial_bid":e["bid"],"initial_ask":e["ask"],
                "exit_bid":exit_bid,"maker_filled":bool(e.get("maker_filled")),
                "maker_return_pct":round(maker_ret*100,5),
                "taker_return_pct":round(taker_ret*100,5),
                "maker_minus_taker_pct":round((maker_ret-taker_ret)*100,5),
                "route_at_open":e.get("route"),"candidate_state":e.get("candidate_state"),
            }
            append(row);closed.append(key)
            st["closed"]=int(st.get("closed",0))+1
            if e.get("maker_filled"):st["maker_fills"]=int(st.get("maker_fills",0))+1
            st["maker_sum"]=float(st.get("maker_sum",0))+maker_ret
            st["taker_sum"]=float(st.get("taker_sum",0))+taker_ret
    for key in closed:eps.pop(key,None)
    save(STATE,st)
    n=max(1,int(st.get("closed",0)))
    status={
        "schema":"andys-bot-r7.5-execution-counterfactual-v1","generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(now)),
        "paper_only":True,"live_locked":True,"can_place_orders":False,
        "open_episodes":len(eps),"closed":int(st.get("closed",0)),
        "maker_fills":int(st.get("maker_fills",0)),
        "maker_fill_rate":(int(st.get("maker_fills",0))/n if st.get("closed") else None),
        "avg_maker_return_pct":(float(st.get("maker_sum",0))/n*100 if st.get("closed") else None),
        "avg_taker_return_pct":(float(st.get("taker_sum",0))/n*100 if st.get("closed") else None),
        "horizon_seconds":HORIZON,"maker_ttl_seconds":MAKER_TTL,
    }
    save(STATUS,status);return status

def main():
    print("R7.5 EXECUTION COUNTERFACTUAL - SHADOW ONLY",flush=True)
    while True:
        try:print(step(),flush=True)
        except Exception as e:print("ERROR",repr(e),flush=True)
        time.sleep(POLL)

if __name__=="__main__":main()