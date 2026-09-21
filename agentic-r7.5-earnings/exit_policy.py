#!/usr/bin/env python3
"""R7.5 shadow exit/profit-protection policy.

Never sends/cancels an order. It recommends a stop level to the existing bot.
The proposed stop can only tighten; it never loosens the current protection.
"""
from __future__ import annotations

from typing import Any
import math


def num(v: Any, d: float = 0.0) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except Exception:
        return d


def recommend_stop(*, entry: float, current: float, highest: float, atr: float,
                   current_stop: float, initial_stop: float, maker_fee: float,
                   taker_fee: float, config: dict) -> dict:
    entry = num(entry)
    current = num(current)
    highest = max(num(highest), current)
    atr = num(atr)
    current_stop = num(current_stop)
    initial_stop = num(initial_stop)
    if min(entry, current, atr) <= 0:
        return {"action": "HOLD_STOP", "stop": current_stop, "reason": "invalid price/ATR"}

    risk_per_unit = max(entry - initial_stop, atr * 0.5)
    if risk_per_unit <= 0:
        return {"action": "HOLD_STOP", "stop": current_stop, "reason": "invalid initial risk"}

    r_high = (highest - entry) / risk_per_unit
    r_now = (current - entry) / risk_per_unit
    slippage = num(config.get("expected_slippage_bps"), 10) / 10_000
    break_even_cost = max(0.0, maker_fee) + max(0.0, taker_fee) + slippage
    fee_aware_break_even = entry * (1 + break_even_cost)

    proposed = max(current_stop, initial_stop)
    reasons = []

    be_trigger = num(config.get("break_even_trigger_r"), 1.0)
    if r_high >= be_trigger:
        proposed = max(proposed, fee_aware_break_even)
        reasons.append(f"fee-aware break-even armed at {r_high:.2f}R")

    trail_trigger = num(config.get("trail_trigger_r"), 1.5)
    if r_high >= trail_trigger:
        trail_mult = num(config.get("trail_atr_mult"), 2.5)
        trail = highest - trail_mult * atr
        proposed = max(proposed, trail)
        reasons.append(f"ATR trail armed at {r_high:.2f}R")

    max_stop = current * (1 - num(config.get("stop_price_buffer_bps"), 5) / 10_000)
    proposed = min(proposed, max_stop)
    proposed = max(proposed, current_stop)

    action = "TIGHTEN_STOP" if proposed > current_stop + 1e-12 else "HOLD_STOP"
    return {
        "action": action,
        "stop": round(proposed, 8),
        "current_stop": current_stop,
        "r_now": round(r_now, 3),
        "r_high": round(r_high, 3),
        "fee_aware_break_even": round(fee_aware_break_even, 8),
        "reasons": reasons,
        "note": "shadow recommendation only",
    }
