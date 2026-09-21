#!/usr/bin/env python3
"""Shadow-only promotion guard for R7.5 execution routes."""
import csv,json,statistics,time
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CSV=ROOT/"execution_counterfactual.csv"
STATUS=ROOT/"state"/"execution_promotion_guard.json"

MIN_SAMPLES=100
MIN_POSITIVE_RATE=0.55
MIN_AVG_TAKER_PCT=0.05
MIN_MAKER_FILL_RATE=0.15

def save(obj):
    raw=json.dumps(obj,indent=2)
    try:
        tmp=STATUS.with_suffix(".tmp");tmp.write_text(raw,encoding="utf-8");tmp.replace(STATUS)
    except PermissionError:
        STATUS.write_text(raw,encoding="utf-8");json.loads(STATUS.read_text(encoding="utf-8"))

def run():
    rows=list(csv.DictReader(CSV.open(encoding="utf-8"))) if CSV.exists() else []
    groups=defaultdict(list)
    for r in rows:
        groups[(r.get("route_at_open") or "UNKNOWN",r.get("candidate_state") or "UNKNOWN")].append(r)
    results=[]
    for (route,state),vals in sorted(groups.items()):
        taker=[float(x.get("taker_return_pct") or 0) for x in vals]
        fills=sum(str(x.get("maker_filled")).lower()=="true" for x in vals)
        n=len(vals); pos=sum(x>0 for x in taker)/n if n else 0
        avg=statistics.mean(taker) if taker else 0
        fill=fills/n if n else 0
        ready=(state=="SHADOW_READY" and n>=MIN_SAMPLES and pos>=MIN_POSITIVE_RATE and avg>=MIN_AVG_TAKER_PCT)
        if route=="MAKER_WAIT":
            ready=ready and fill>=MIN_MAKER_FILL_RATE
        reasons=[]
        if state!="SHADOW_READY":reasons.append("observations are not SHADOW_READY")
        if n<MIN_SAMPLES:reasons.append(f"only {n}/{MIN_SAMPLES} observations")
        if pos<MIN_POSITIVE_RATE:reasons.append(f"positive rate {pos:.1%} below {MIN_POSITIVE_RATE:.0%}")
        if avg<MIN_AVG_TAKER_PCT:reasons.append(f"avg taker return {avg:.3f}% below {MIN_AVG_TAKER_PCT:.2f}%")
        if route=="MAKER_WAIT" and fill<MIN_MAKER_FILL_RATE:reasons.append(f"maker fill {fill:.1%} below {MIN_MAKER_FILL_RATE:.0%}")
        results.append({"route":route,"candidate_state":state,"samples":n,"positive_rate":round(pos,4),"avg_taker_return_pct":round(avg,5),"maker_fill_rate":round(fill,4),"promotion_ready":bool(ready),"reasons":reasons})
    out={"schema":"andys-bot-r7.5-execution-promotion-v1","generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"shadow_only":True,"can_change_live_execution":False,"any_promotion_ready":any(x["promotion_ready"] for x in results),"routes":results}
    STATUS.parent.mkdir(parents=True,exist_ok=True);save(out);return out

if __name__=="__main__":
    print(json.dumps(run(),indent=2))