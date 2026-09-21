#!/usr/bin/env python3
"""R7.5 shadow smart-execution selector.

Chooses between MAKER_WAIT, TAKER_NOW, WAIT_RETEST and NO_TRADE.
It never submits, cancels or edits a real order.
"""
from __future__ import annotations
import math
from typing import Any

def n(v: Any, d: float = 0.0) -> float:
    try:
        x=float(v)
        return x if math.isfinite(x) else d
    except Exception:
        return d

def clamp(x: float, lo: float=0.0, hi: float=1.0) -> float:
    return max(lo,min(hi,x))

def fill_probability(mm: dict, asset: dict) -> dict:
    q=max(0,n(mm.get("quote_episodes")))
    f=max(0,n(mm.get("bid_fills")))
    base=(f/q) if q>=20 else 0.10
    opp=asset.get("market_opportunity") or {}
    flow=asset.get("order_flow") or {}
    activity=n(opp.get("activity_score"),50)
    flow_score=n(flow.get("score"),0)
    book=asset.get("coinbase_orderbook") or {}
    spread=n(book.get("spread_bps"),999)
    p=base
    p += clamp((activity-50)/50,0,1)*0.05
    if flow_score < -15: p += 0.04
    if 8 <= spread <= 40: p += 0.03
    p=clamp(p,0.03,0.55)
    return {"probability":round(p,4),"baseline":round(base,4),"quote_episodes":int(q),"bid_fills":int(f)}

def route(candidate: dict, asset: dict, mm: dict, config: dict) -> dict:
    state=str(candidate.get("state") or "").upper()
    if state!="SHADOW_READY":
        return {"route":"NO_TRADE","reason":"candidate is not SHADOW_READY","can_execute":False}
    opp=asset.get("market_opportunity") or {}
    if bool(opp.get("chase_risk")):
        return {"route":"WAIT_RETEST","reason":"chase/extension risk","can_execute":False}

    fee=candidate.get("fee_schedule") or {}
    maker=n(fee.get("maker")); taker=n(fee.get("taker"))
    edge=candidate.get("edge") or {}
    expected=n(edge.get("expected_return"))
    maker_net_bps=n(edge.get("net_edge_bps"))
    spread_bps=n((candidate.get("liquidity") or {}).get("spread_bps"))
    slip_bps=n(config.get("taker_slippage_bps"),10)
    buffer_bps=n(config.get("taker_safety_buffer_bps"),15)
    taker_cost=2*taker + 2*(slip_bps/10000.0) + (spread_bps/10000.0) + buffer_bps/10000.0
    taker_net=(expected-taker_cost)*10000.0

    fp=fill_probability(mm,asset)
    activity=n(opp.get("activity_score"),50)
    mtf=abs(n((asset.get("multi_timeframe") or {}).get("score")))
    urgency=clamp((activity-50)/50,0,1)*55 + clamp(mtf/70,0,1)*30 + clamp(expected/0.03,0,1)*15

    min_taker=n(config.get("min_taker_net_edge_bps"),35)
    min_maker=n(config.get("min_maker_net_edge_bps"),20)
    min_fill=n(config.get("min_maker_fill_probability"),0.18)
    urgent=n(config.get("taker_urgency_score"),75)

    if taker_net >= min_taker and urgency >= urgent:
        chosen="TAKER_NOW"; reason="strong net edge + high urgency"
    elif maker_net_bps >= min_maker and fp["probability"] >= min_fill:
        chosen="MAKER_WAIT"; reason="maker edge is positive and fill odds are acceptable"
    elif taker_net >= max(min_taker,60):
        chosen="TAKER_NOW"; reason="large taker net edge justifies immediacy"
    else:
        chosen="WAIT_RETEST"; reason="maker fill odds too low and taker edge not strong enough"

    return {
        "route":chosen,"reason":reason,"can_execute":False,
        "maker_net_edge_bps":round(maker_net_bps,2),
        "taker_net_edge_bps":round(taker_net,2),
        "urgency_score":round(urgency,1),
        "maker_fill":fp,
        "assumptions":{"taker_slippage_bps_per_side":slip_bps,"safety_buffer_bps":buffer_bps},
    }
DEFAULT_CONFIG={
    "taker_slippage_bps":10.0,
    "taker_safety_buffer_bps":15.0,
    "min_taker_net_edge_bps":35.0,
    "min_maker_net_edge_bps":20.0,
    "min_maker_fill_probability":0.18,
    "taker_urgency_score":75.0,
}