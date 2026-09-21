#!/usr/bin/env python3
"""Andy's Bot R7.5 earnings/risk policy engine.

Deterministic, shadow-only policy layer:
strategy health -> regime route -> fee/edge gate -> liquidity gate ->
adaptive sizing -> maker-first execution plan.

This module never places orders. It only returns proposals for the existing
bot preview/approval layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import math


def num(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def bps(value: float) -> float:
    return value * 10_000.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class FeeSchedule:
    maker: float
    taker: float
    source: str
    updated_utc: str

    @property
    def valid(self) -> bool:
        return 0 <= self.maker < 0.05 and 0 <= self.taker < 0.05


def fee_schedule_from_summary(summary: dict | None, config: dict) -> FeeSchedule:
    tier = (summary or {}).get("fee_tier") or {}
    maker = num(tier.get("maker_fee_rate"), -1)
    taker = num(tier.get("taker_fee_rate"), -1)
    if maker >= 0 and taker >= 0:
        return FeeSchedule(maker, taker, "coinbase_transaction_summary", utc_now())
    return FeeSchedule(
        num(config.get("fallback_maker_fee"), 0.0025),
        num(config.get("fallback_taker_fee"), 0.0060),
        "config_fallback",
        utc_now(),
    )


def _row_for_strategy(lab_status: dict, product: str, strategy: str) -> dict:
    rows = [
        r for r in lab_status.get("results", [])
        if str(r.get("market", "")).upper() == product.upper()
        and str(r.get("strategy", "")).lower() == strategy.lower()
    ]
    return rows[0] if rows else {}


def strategy_health(lab_status: dict, product: str, strategy: str, config: dict,
                    recent_trades: list[dict] | None = None) -> dict:
    row = _row_for_strategy(lab_status, product, strategy)
    if not row:
        return {"score": 0.0, "state": "OFF", "reasons": ["no walk-forward evidence"]}
    m = row.get("metrics") or {}
    folds = row.get("fold_stats") or []
    score = 50.0
    reasons = []

    if row.get("verdict") == "PASS":
        score += 14
    else:
        score -= 14
        reasons.append("walk-forward verdict is FAIL")

    pf = num(m.get("pf"))
    score += clamp((pf - 1.0) / 1.0, -1, 1) * 16
    dd = num(m.get("mdd"), 1.0)
    score += clamp((0.25 - dd) / 0.25, -1, 1) * 10
    stability = num(m.get("param_stability"))
    score += (stability - 0.5) * 14
    positive_ratio = num(m.get("positive_folds")) / max(1.0, num(m.get("folds"), len(folds) or 1))
    score += (positive_ratio - 0.5) * 14

    recent_fold_returns = [num(f.get("return")) for f in folds[-2:]]
    if len(recent_fold_returns) == 2 and all(x <= 0 for x in recent_fold_returns):
        score -= 24
        reasons.append("last two unseen folds are negative")
    elif recent_fold_returns and sum(recent_fold_returns) > 0:
        score += 5

    recent_trades = recent_trades or []
    if len(recent_trades) >= int(config.get("health_recent_trade_min", 10)):
        pnls = [num(t.get("pnl")) for t in recent_trades]
        gross_win = sum(x for x in pnls if x > 0)
        gross_loss = abs(sum(x for x in pnls if x <= 0))
        live_pf = gross_win / gross_loss if gross_loss else (3.0 if gross_win else 0.0)
        if sum(pnls) <= 0 or live_pf < num(config.get("health_recent_pf_min"), 1.0):
            score -= 18
            reasons.append("recent live/shadow performance is weak")
        elif live_pf >= 1.25:
            score += 8

    score = round(max(0.0, min(100.0, score)), 1)
    off = num(config.get("health_off_score"), 45)
    ready = num(config.get("health_ready_score"), 65)
    state = "OFF" if score < off else ("WATCH" if score < ready else "READY")
    return {
        "score": score,
        "state": state,
        "reasons": reasons,
        "strategy": strategy,
        "product": product,
        "verdict": row.get("verdict", "UNKNOWN"),
        "last_two_fold_returns": recent_fold_returns,
    }


def regime_route(strategy: str, asset: dict, snapshot: dict) -> dict:
    strategy = strategy.lower()
    mtf = num((asset.get("multi_timeframe") or {}).get("score"))
    opportunity = asset.get("market_opportunity") or {}
    activity = num(opportunity.get("activity_score"), 50)
    chase = bool(opportunity.get("chase_risk"))
    regime = snapshot.get("btc_regime_breadth") or {}
    btc_state = str((regime.get("btc") or {}).get("state") or "").upper()
    breadth = str((regime.get("breadth") or {}).get("state") or "").upper()
    reasons = []
    allowed = True
    score = 50.0

    if strategy == "breakout":
        score += max(-20, min(20, mtf * 0.35))
        score += max(-12, min(12, (activity - 50) * 0.25))
        if chase:
            allowed = False
            reasons.append("breakout blocked by chase/extension risk")
        if btc_state in {"CRASH", "BREAKDOWN", "BEARISH_BREAKDOWN"}:
            allowed = False
            reasons.append("breakout blocked by defensive BTC regime")
    elif strategy == "trend":
        score += max(-25, min(25, mtf * 0.45))
        if abs(mtf) < 10:
            reasons.append("trend evidence is weak")
    elif strategy == "meanrev":
        score -= abs(mtf) * 0.3
        if abs(mtf) > 35:
            allowed = False
            reasons.append("mean-reversion blocked in strong trend")
    if breadth in {"WEAK", "NARROW"}:
        score -= 8
        reasons.append("breadth is weak")
    return {"allowed": allowed, "score": round(max(0, min(100, score)), 1), "reasons": reasons}


def liquidity_gate(book: dict, amount_gbp: float, config: dict) -> dict:
    bid = num(book.get("best_bid"))
    ask = num(book.get("best_ask"))
    bid_depth = num(book.get("bid_depth_gbp"))
    ask_depth = num(book.get("ask_depth_gbp"))
    status = str(book.get("market_status") or "FULL_TRADING").upper()
    if bid <= 0 or ask <= 0 or ask <= bid:
        return {"allowed": False, "score": 0.0, "spread_bps": None, "reasons": ["invalid order book"]}
    mid = (bid + ask) / 2
    spread_bps = (ask - bid) / mid * 10_000
    reasons = []
    allowed = True

    if status in {"CANCEL_ONLY", "TRADING_DISABLED", "VIEW_ONLY", "AUCTION"}:
        allowed = False
        reasons.append(f"market status {status} is not suitable")
    max_spread = num(config.get("max_spread_bps"), 15)
    if spread_bps > max_spread:
        allowed = False
        reasons.append(f"spread {spread_bps:.1f} bps exceeds {max_spread:.1f}")

    depth_multiple = num(config.get("min_depth_multiple"), 8)
    depth_required = max(1.0, amount_gbp * depth_multiple)
    min_depth = min(bid_depth, ask_depth) if bid_depth and ask_depth else 0
    if min_depth < depth_required:
        allowed = False
        reasons.append("visible GBP depth is too thin")

    spread_score = clamp(1 - spread_bps / max(max_spread, 1), 0, 1)
    depth_score = clamp(min_depth / max(depth_required * 2, 1), 0, 1)
    return {
        "allowed": allowed,
        "score": round((0.55 * spread_score + 0.45 * depth_score) * 100, 1),
        "spread_bps": round(spread_bps, 3),
        "mid": mid,
        "best_bid": bid,
        "best_ask": ask,
        "bid_depth_gbp": bid_depth,
        "ask_depth_gbp": ask_depth,
        "reasons": reasons,
    }


def edge_gate(expected_return: float, fee: FeeSchedule, liquidity: dict, config: dict,
              maker_entry: bool = True, protective_exit_taker: bool = True) -> dict:
    entry_fee = fee.maker if maker_entry else fee.taker
    exit_fee = fee.taker if protective_exit_taker else fee.maker
    slippage = num(config.get("expected_slippage_bps"), 10) / 10_000
    spread_cost = 0.0 if maker_entry else num(liquidity.get("spread_bps")) / 10_000
    buffer_ = num(config.get("edge_safety_buffer_bps"), 20) / 10_000
    total_cost = entry_fee + exit_fee + slippage + spread_cost + buffer_
    net = expected_return - total_cost
    min_net = num(config.get("min_net_edge_bps"), 20) / 10_000
    return {
        "allowed": net >= min_net,
        "expected_return": expected_return,
        "entry_fee": entry_fee,
        "exit_fee": exit_fee,
        "slippage_assumption": slippage,
        "spread_cost": spread_cost,
        "safety_buffer": buffer_,
        "total_cost": total_cost,
        "net_edge": net,
        "net_edge_bps": round(bps(net), 2),
        "min_net_edge_bps": round(bps(min_net), 2),
    }


def adaptive_size(signal_score: float, health: dict, regime: dict, liquidity: dict,
                  edge: dict, portfolio: dict, config: dict) -> dict:
    hard_cap = min(
        num(config.get("max_order_gbp_hard"), 10),
        max(0.0, num(portfolio.get("remaining_exposure_gbp"), config.get("max_exposure_gbp_hard", 20))),
    )
    if hard_cap <= 0:
        return {"amount_gbp": 0.0, "factors": {}, "reason": "no exposure headroom"}

    quality = clamp((signal_score - 55) / 35, 0, 1)
    health_f = clamp(num(health.get("score")) / 100, 0, 1)
    regime_f = clamp(num(regime.get("score")) / 100, 0, 1)
    liquidity_f = clamp(num(liquidity.get("score")) / 100, 0, 1)
    edge_bps_ = max(0, num(edge.get("net_edge_bps")))
    edge_f = clamp(edge_bps_ / max(1, num(config.get("full_size_net_edge_bps"), 150)), 0, 1)

    combined = quality * health_f * regime_f * liquidity_f * edge_f
    floor = num(config.get("min_size_fraction"), 0.20)
    fraction = max(floor, combined) if all([
        health.get("state") == "READY",
        regime.get("allowed"),
        liquidity.get("allowed"),
        edge.get("allowed"),
    ]) else 0.0

    depth_cap_fraction = num(config.get("depth_order_fraction"), 0.10)
    visible_depth = min(num(liquidity.get("bid_depth_gbp")), num(liquidity.get("ask_depth_gbp")))
    depth_cap = visible_depth * depth_cap_fraction if visible_depth > 0 else 0.0
    amount = min(hard_cap * fraction, depth_cap or hard_cap)
    min_order = num(config.get("min_shadow_order_gbp"), 1.0)
    if amount < min_order:
        amount = 0.0
    return {
        "amount_gbp": round(amount, 2),
        "fraction_of_hard_cap": round(fraction, 4),
        "factors": {
            "quality": round(quality, 3),
            "health": round(health_f, 3),
            "regime": round(regime_f, 3),
            "liquidity": round(liquidity_f, 3),
            "edge": round(edge_f, 3),
        },
    }


def maker_first_plan(side: str, liquidity: dict, edge: dict, amount_gbp: float, config: dict,
                     fee: FeeSchedule) -> dict:
    side = side.upper()
    if amount_gbp <= 0 or not edge.get("allowed"):
        return {"action": "NO_ORDER", "reason": "edge/size gate failed"}
    maker_price = num(liquidity.get("best_bid" if side == "BUY" else "best_ask"))
    if maker_price <= 0:
        return {"action": "NO_ORDER", "reason": "no maker price"}
    allow_taker_fallback = False
    if fee.source != "config_fallback":
        taker_edge = edge_gate(
            num(edge.get("expected_return")),
            fee,
            liquidity,
            config,
            maker_entry=False,
            protective_exit_taker=True,
        )
        allow_taker_fallback = bool(taker_edge.get("allowed")) and bool(config.get("allow_shadow_taker_fallback", False))
    return {
        "action": "POST_ONLY_LIMIT",
        "side": side,
        "price": maker_price,
        "amount_gbp": round(amount_gbp, 2),
        "post_only": True,
        "timeout_seconds": int(config.get("maker_timeout_seconds", 45)),
        "max_reprices": int(config.get("maker_max_reprices", 3)),
        "reprice_rule": "refresh at current best same-side price without crossing",
        "on_timeout": "CANCEL" if not allow_taker_fallback else "SHADOW_REVIEW_TAKER",
        "taker_fallback_allowed": allow_taker_fallback,
        "note": "proposal only; existing bot remains execution authority",
    }


def evaluate_earnings_candidate(*, product: str, strategy: str, signal_score: float,
                                expected_return: float, asset: dict, snapshot: dict,
                                lab_status: dict, book: dict, fee_summary: dict | None,
                                portfolio: dict, config: dict,
                                recent_trades: list[dict] | None = None) -> dict:
    fee = fee_schedule_from_summary(fee_summary, config)
    health = strategy_health(lab_status, product, strategy, config, recent_trades)
    regime = regime_route(strategy, asset, snapshot)
    provisional = min(
        num(config.get("max_order_gbp_hard"), 10),
        num(portfolio.get("remaining_exposure_gbp"), config.get("max_exposure_gbp_hard", 20)),
    )
    liquidity = liquidity_gate(book, provisional, config)
    edge = edge_gate(expected_return, fee, liquidity, config)
    sizing = adaptive_size(signal_score, health, regime, liquidity, edge, portfolio, config)
    execution = maker_first_plan("BUY", liquidity, edge, sizing["amount_gbp"], config, fee)

    reasons = []
    if health["state"] != "READY":
        reasons.append(f"strategy health is {health['state']}")
    if not regime["allowed"]:
        reasons.extend(regime["reasons"])
    if not liquidity["allowed"]:
        reasons.extend(liquidity["reasons"])
    if not edge["allowed"]:
        reasons.append(f"net edge {edge['net_edge_bps']:.1f} bps below requirement")
    ready = not reasons and sizing["amount_gbp"] > 0 and execution["action"] == "POST_ONLY_LIMIT"
    state = "SHADOW_READY" if ready else ("WATCH" if health["state"] != "OFF" else "REJECT")
    return {
        "schema": "andys-bot-r7.5-earnings-candidate-v1",
        "mode": "SHADOW_ONLY",
        "product": product,
        "strategy": strategy,
        "state": state,
        "reasons": list(dict.fromkeys(reasons)),
        "fee_schedule": fee.__dict__,
        "health": health,
        "regime": regime,
        "liquidity": liquidity,
        "edge": edge,
        "sizing": sizing,
        "execution": execution,
        "guardrails": {
            "live_orders": False,
            "transfers": False,
            "risk_changes": False,
            "max_positions_hard": int(config.get("max_positions_hard", 8)),
            "max_order_gbp_hard": num(config.get("max_order_gbp_hard"), 10),
            "max_exposure_gbp_hard": num(config.get("max_exposure_gbp_hard"), 20),
        },
    }
