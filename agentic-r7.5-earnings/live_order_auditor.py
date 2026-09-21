#!/usr/bin/env python3
"""Read-only auditor for real-money live entries.

Watches the existing local /api/live payload and authoritative live ledger.
Records whether each newly observed live position/order was supported by the
R7.5 gate at observation time. Never places, cancels, edits or previews orders.
"""
from __future__ import annotations
import json,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATUS=ROOT/"state"/"live_order_audit_status.json"
AUDIT=ROOT/"state"/"live_order_audit.jsonl"
SEEN=ROOT/"state"/"live_order_audit_seen.json"
R75=ROOT/"state"/"r7_5_live_shadow_status.json"
URL="http://127.0.0.1:8787/api/live"

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
    req=urllib.request.Request(URL,headers={"User-Agent":"AndysBot-R75-LiveAudit"})
    with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)

def r75_for(product):
    d=load(R75,{})
    row=next((x for x in (d.get("candidates") or []) if str((x or {}).get("product") or "").upper()==product.upper()),None)
    return d,row
def once():
    d=live();lc=d.get("live_canary") or {};now=time.time()
    seen=load(SEEN,{"orders":[]});known=set(seen.get("orders") or [])
    if not SEEN.exists():
        known={str((pos or {}).get("order_id") or "") for pos in (lc.get("positions") or {}).values()}
        known={x for x in known if x}; seen["orders"]=sorted(known); save(SEEN,seen)
    new_rows=[];mismatches=0
    for sym,pos in (lc.get("positions") or {}).items():
        oid=str(pos.get("order_id") or "")
        if not oid or oid in known:continue
        product=str(pos.get("product_id") or f"{sym}-GBP")
        status,row=r75_for(product)
        age=None
        try:age=max(0.0,time.time()-R75.stat().st_mtime)
        except Exception:pass
        validation=(row or {}).get("execution_validation") or {}
        supported=bool(
            row and age is not None and age<=180
            and str(row.get("state") or "").upper()=="SHADOW_READY"
            and str(((row.get("smart_execution") or {}).get("route") or "")).upper()=="TAKER_NOW"
            and str(((validation.get("taker") or {}).get("verdict") or "")).upper()=="PASS"
        )
        rec={
            "utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(now)),
            "symbol":sym,"product":product,"order_id":oid,
            "entry_price":pos.get("entry_price"),"entry_cost_gbp":pos.get("entry_cost_gbp"),
            "r75_supported":supported,
            "r75_state":(row or {}).get("state"),
            "r75_strategy":(row or {}).get("strategy"),
            "r75_route":((row or {}).get("smart_execution") or {}).get("route"),
            "r75_taker_verdict":((validation.get("taker") or {}).get("verdict")),
            "r75_age_seconds":age,
            "note":"observational only; order already existed before audit record",
        }
        with AUDIT.open("a",encoding="utf-8") as f:f.write(json.dumps(rec,separators=(",",":"))+"\n")
        new_rows.append(rec);known.add(oid)
        if not supported:mismatches+=1
    seen["orders"]=sorted(known);save(SEEN,seen)
    out={
        "schema":"andys-bot-r7.5-live-order-audit-v1",
        "generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(now)),
        "read_only":True,"can_place_orders":False,
        "known_live_orders":len(known),"new_records":len(new_rows),
        "new_mismatches":mismatches,"last_records":new_rows[-5:],
    }
    save(STATUS,out);return out

def main():
    print("R7.5 LIVE ORDER AUDITOR - READ ONLY",flush=True)
    while True:
        try:print(once(),flush=True)
        except Exception as e:print("ERROR",repr(e),flush=True)
        time.sleep(30)

if __name__=="__main__":main()