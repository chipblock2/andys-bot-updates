#!/usr/bin/env python3
"""R7.5 live shadow bridge for Andy's Bot.

Reads the existing local /api/live payload and R7.5 walk-forward status.
Writes recommendations only. It has no order/approval/transfer endpoints.
"""
import json, time, urllib.request
from pathlib import Path
from earnings_engine import evaluate_earnings_candidate

ROOT=Path(__file__).resolve().parent
LAB=ROOT/"state"/"strategy_lab_status.json"
STATUS=ROOT/"state"/"r7_5_live_shadow_status.json"
AUDIT=ROOT/"state"/"r7_5_live_shadow_audit.jsonl"
URL="http://127.0.0.1:8787/api/live"
CANDIDATES=[("ETH-GBP","breakout"),("ETH-GBP","trend"),("BTC-GBP","breakout")]

def load_json(path,default=None):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return {} if default is None else default

def get_live():
    req=urllib.request.Request(URL,headers={"User-Agent":"AndysBot-R75-Shadow"})
    with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)

def live_config(d):
    s=d.get("settings") or {}
    return {
        "mode":"SHADOW_ONLY",
        "max_positions_hard":int(s.get("live_max_positions",8)),
        "max_order_gbp_hard":float(s.get("live_order_cap_gbp",15.0)),
        "max_exposure_gbp_hard":float(s.get("live_max_total_exposure_gbp",100.0)),
        "fallback_maker_fee":float(s.get("coinbase_maker_fee",0.0006)),
        "fallback_taker_fee":float(s.get("coinbase_taker_fee",0.0016)),
        "require_account_fees_for_ready":True,
        "expected_slippage_bps":10,"edge_safety_buffer_bps":15,
        "min_net_edge_bps":20,"full_size_net_edge_bps":150,
        "max_spread_bps":float(s.get("market_quality_max_spread_bps",120.0)),
        "min_depth_multiple":max(2.0,float(s.get("liquidity_min_depth_multiple",2.0))),
        "depth_order_fraction":0.10,"health_ready_score":65,"health_off_score":45,
        "health_recent_trade_min":10,"health_recent_pf_min":1.0,
        "min_size_fraction":max(0.05,float(s.get("live_dynamic_min_allocation_pct",0.05))),
        "min_shadow_order_gbp":float(s.get("live_dynamic_min_order_gbp",4.0)),
        "maker_timeout_seconds":45,"maker_max_reprices":3,
        "allow_shadow_taker_fallback":False,
    }

def fee_summary(d):
    f=d.get("fee_profile") or {}
    return {"fee_tier":{"pricing_tier":f.get("pricing_tier"),
        "maker_fee_rate":f.get("maker_fee"),"taker_fee_rate":f.get("taker_fee")}} if f.get("configured") and not f.get("stale") else None

def portfolio(d,cfg):
    lc=d.get("live_canary") or {}; exposure=float(lc.get("exposure_gbp") or 0.0)
    maxexp=min(float(cfg["max_exposure_gbp_hard"]),float(lc.get("max_exposure_gbp") or cfg["max_exposure_gbp_hard"]))
    return {"remaining_exposure_gbp":max(0.0,maxexp-exposure),"exposure_gbp":exposure,
        "max_exposure_gbp":maxexp,"open_positions":len((lc.get("positions") or {})),
        "max_positions":int(lc.get("max_positions") or cfg["max_positions_hard"])}

def book_from_asset(a):
    b=a.get("coinbase_orderbook") or {}
    return {"best_bid":b.get("best_bid"),"best_ask":b.get("best_ask"),
        "bid_depth_gbp":b.get("bid_depth_5_gbp"),"ask_depth_gbp":b.get("ask_depth_5_gbp"),
        "market_status":"FULL_TRADING"}

def run_once():
    d=get_live(); lab=load_json(LAB); cfg=live_config(d); fees=fee_summary(d); port=portfolio(d,cfg); rows=[]
    for product,strategy in CANDIDATES:
        sym=product.split("-")[0]; a=(d.get("assets") or {}).get(sym) or {}
        score=float((a.get("decision_council") or {}).get("score") or 0.0)
        expected=float(a.get("expected_return") or 0.0)
        row=evaluate_earnings_candidate(product=product,strategy=strategy,signal_score=score,
            expected_return=expected,asset=a,snapshot=d,lab_status=lab,book=book_from_asset(a),
            fee_summary=fees,portfolio=port,config=cfg)
        base_action=str(a.get("action") or "HOLD").upper(); row["base_action"]=base_action; row["base_reason"]=a.get("reason") or ""
        if base_action not in {"BUY","LONG","TRADE"}:
            row["state"]="WATCH" if row["health"]["state"]!="OFF" else "REJECT"
            row["execution"]={"action":"NO_ORDER","reason":"base live engine is not BUY/LONG/TRADE"}
            row["reasons"]=list(dict.fromkeys(row.get("reasons",[])+[f"base live engine says {base_action}"]))
        rows.append(row)
    rows.sort(key=lambda x:(x["state"]=="SHADOW_READY",x["health"]["score"],x["edge"]["net_edge_bps"]),reverse=True)
    out={"schema":"andys-bot-r7.5-live-shadow-v1","generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "mode":"SHADOW_ONLY","live_api":URL,"fee_profile":d.get("fee_profile"),"portfolio":port,
        "candidates":rows,"best":rows[0] if rows else None,"live_order_cap_gbp":cfg["max_order_gbp_hard"],
        "live_exposure_cap_gbp":cfg["max_exposure_gbp_hard"],"can_place_orders":False}
    STATUS.parent.mkdir(parents=True,exist_ok=True); tmp=STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(out,indent=2),encoding="utf-8"); tmp.replace(STATUS)
    with AUDIT.open("a",encoding="utf-8") as f:f.write(json.dumps({"utc":out["generated_utc"],"best":(out.get("best") or {}).get("product"),"state":(out.get("best") or {}).get("state"),"can_place_orders":False})+"\n")
    return out

def main():
    while True:
        try:run_once()
        except Exception as e:
            with AUDIT.open("a",encoding="utf-8") as f:f.write(json.dumps({"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"error":repr(e)})+"\n")
        time.sleep(60)

if __name__=="__main__":main()
