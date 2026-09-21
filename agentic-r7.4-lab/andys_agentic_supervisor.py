#!/usr/bin/env python3
"""Deterministic multi-stage supervisor for Andy's Bot R7.4.

Architecture inspired by robust multi-agent trading systems:
Signal -> Bull/Bear evidence -> Risk judge -> Shadow allocation proposal.
No order, transfer, approval or risk-change endpoint is called here.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def num(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except Exception:
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _symbol_key(symbol: str) -> str:
    return str(symbol).upper().replace("/", "-").replace("_", "-")


def _asset_product(symbol: str) -> str:
    symbol = _symbol_key(symbol)
    if "-" in symbol:
        return symbol
    return f"{symbol}-GBP"


def load_lab_status(path: str | Path | None) -> dict:
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def lab_evidence(lab_status: dict, symbol: str) -> dict:
    product = _asset_product(symbol)
    candidates = [r for r in lab_status.get("results", []) if _symbol_key(r.get("market", "")) == product]
    if not candidates:
        return {"available": False, "product": product, "score": 50.0, "verdict": "UNKNOWN"}
    candidates.sort(
        key=lambda r: (
            r.get("verdict") == "PASS",
            num((r.get("metrics") or {}).get("monthly")),
            num((r.get("metrics") or {}).get("pf")),
        ),
        reverse=True,
    )
    row = candidates[0]
    m = row.get("metrics") or {}
    pass_bonus = 12 if row.get("verdict") == "PASS" else -8
    score = 50 + pass_bonus
    score += clamp((num(m.get("pf"), 1.0) - 1.0) * 18, -15, 18)
    score -= clamp(num(m.get("mdd")) * 50, 0, 20)
    score += clamp((num(m.get("positive_folds")) / max(1, num(m.get("folds"), 4)) - 0.5) * 24, -12, 12)
    score += clamp((num(m.get("param_stability"), 0.5) - 0.5) * 20, -10, 10)
    return {
        "available": True,
        "product": product,
        "strategy": row.get("strategy"),
        "verdict": row.get("verdict", "UNKNOWN"),
        "score": round(clamp(score), 1),
        "metrics": m,
    }


def signal_stage(symbol: str, asset: dict, snapshot: dict, lab_status: dict | None = None) -> dict:
    dc = asset.get("decision_council") or {}
    cal = asset.get("confidence_calibration") or {}
    mtf = asset.get("multi_timeframe") or {}
    opp = asset.get("market_opportunity") or {}
    edge = asset.get("edge_profile") or {}
    social = asset.get("news_social") or {}
    perp = asset.get("okx_intelligence") or {}
    quality = asset.get("market_quality") or {}
    raw_prob = num(asset.get("ensemble_probability"), 0.5)
    probability = num(asset.get("calibrated_probability"), num(cal.get("calibrated_probability"), raw_prob))
    expected = num(asset.get("expected_return"))
    required = num(asset.get("required_edge"))
    edge_multiple = expected / required if required > 0 else 0.0
    edge_score = 0.0 if edge_multiple <= 0 else (100.0 if edge_multiple >= 2 else clamp((edge_multiple - 0.55) / 1.45 * 100))
    lab = lab_evidence(lab_status or {}, symbol)
    components = {
        "council": clamp(num(dc.get("score"), 50)),
        "probability": clamp(probability * 100),
        "cost_adjusted_edge": edge_score,
        "multi_timeframe": clamp(50 + num(mtf.get("score")) * 0.5),
        "activity": clamp(num(opp.get("activity_score"), 50)),
        "coin_edge": clamp(num(edge.get("edge_score"), 50)),
        "news_social": clamp(50 + num(social.get("score")) * 0.5),
        "perp_context": clamp(50 + num(perp.get("score")) * 0.5),
        "market_quality": clamp(num(quality.get("score"), 60)),
        "walk_forward": lab["score"],
    }
    weights = {
        "council": 0.20,
        "probability": 0.14,
        "cost_adjusted_edge": 0.18,
        "multi_timeframe": 0.10,
        "activity": 0.07,
        "coin_edge": 0.07,
        "news_social": 0.04,
        "perp_context": 0.05,
        "market_quality": 0.07,
        "walk_forward": 0.08,
    }
    total = sum(components[k] * weights[k] for k in weights)
    blockers, cautions, positives = [], [], []
    action = str(asset.get("action") or "HOLD").upper()
    if required > 0 and expected < required:
        blockers.append("expected move does not clear estimated costs")
    if opp.get("chase_risk"):
        blockers.append("extension/chase risk")
        total -= 12
    if components["market_quality"] < 45:
        blockers.append("market quality too weak")
    if action not in {"BUY", "LONG", "TRADE"}:
        cautions.append(f"base engine says {action}")
        total -= 5
    regime = snapshot.get("btc_regime_breadth") or {}
    btc_state = str((regime.get("btc") or {}).get("state") or "").upper()
    breadth_state = str((regime.get("breadth") or {}).get("state") or "").upper()
    if btc_state in {"BREAKDOWN", "CRASH", "BEARISH_BREAKDOWN"}:
        cautions.append("BTC regime is defensive")
        total -= 10
    if breadth_state in {"WEAK", "NARROW"}:
        cautions.append("market breadth is weak")
        total -= 6
    if lab["available"] and lab["verdict"] != "PASS":
        cautions.append(f"walk-forward validation did not pass ({lab.get('strategy')})")
        total -= 5
    if components["council"] >= 75:
        positives.append("decision council strong")
    if edge_multiple >= 1.35:
        positives.append(f"expected edge clears costs by {edge_multiple:.2f}x")
    if components["multi_timeframe"] >= 65:
        positives.append("multi-timeframe trend supportive")
    if lab["available"] and lab["verdict"] == "PASS":
        positives.append(f"walk-forward validation passed ({lab.get('strategy')})")
    return {
        "symbol": _symbol_key(symbol),
        "action": action,
        "score": round(clamp(total), 1),
        "probability": round(probability, 4),
        "expected_return": round(expected, 8),
        "required_edge": round(required, 8),
        "edge_multiple": round(edge_multiple, 3),
        "components": {k: round(v, 1) for k, v in components.items()},
        "lab": lab,
        "blockers": blockers,
        "cautions": cautions,
        "positives": positives,
        "reason": asset.get("reason") or "",
    }


def bull_stage(signal: dict) -> dict:
    points = list(signal.get("positives") or [])
    c = signal.get("components") or {}
    if c.get("probability", 0) >= 62:
        points.append("calibrated probability is supportive")
    if c.get("market_quality", 0) >= 65:
        points.append("market quality is healthy")
    return {"strength": round(clamp(signal["score"] + 4 * len(points) - 50), 1), "points": points[:6]}


def bear_stage(signal: dict) -> dict:
    risks = list(signal.get("blockers") or []) + list(signal.get("cautions") or [])
    c = signal.get("components") or {}
    if c.get("market_quality", 50) < 55:
        risks.append("market quality is only marginal")
    if signal.get("edge_multiple", 0) < 1.2:
        risks.append("cost-adjusted edge margin is thin")
    severity = 12 * len(signal.get("blockers") or []) + 6 * len(signal.get("cautions") or [])
    severity += max(0, 60 - c.get("market_quality", 60)) * 0.5
    return {"severity": round(clamp(severity), 1), "risks": list(dict.fromkeys(risks))[:8]}


def portfolio_state(snapshot: dict, config: dict) -> dict:
    live = snapshot.get("live_canary") or {}
    positions = live.get("positions") or {}
    if not isinstance(positions, dict):
        positions = {}
    bot_max = int(num(live.get("max_positions"), config["max_positions_hard"]))
    max_positions = min(config["max_positions_hard"], bot_max if bot_max > 0 else config["max_positions_hard"])
    max_exposure = min(config["max_exposure_gbp_hard"], num(live.get("max_exposure_gbp"), config["max_exposure_gbp_hard"]))
    exposure = num(live.get("exposure_gbp"))
    return {
        "positions": positions,
        "open_positions": len(positions),
        "max_positions": max_positions,
        "exposure_gbp": round(exposure, 2),
        "max_exposure_gbp": round(max_exposure, 2),
        "remaining_exposure_gbp": round(max(0.0, max_exposure - exposure), 2),
    }


def risk_judge(signal: dict, bull: dict, bear: dict, portfolio: dict, config: dict) -> dict:
    vetoes = list(signal.get("blockers") or [])
    if portfolio["open_positions"] >= portfolio["max_positions"]:
        vetoes.append("portfolio position limit reached")
    if portfolio["remaining_exposure_gbp"] <= 0:
        vetoes.append("portfolio exposure limit reached")
    if bear["severity"] >= 55:
        vetoes.append("bear/risk evidence is too strong")
    if signal["score"] < config["watch_min_score"]:
        vetoes.append("quality score below watch threshold")
    adjusted = signal["score"] + min(8, bull["strength"] * 0.08) - min(18, bear["severity"] * 0.18)
    return {
        "approved_shadow": not vetoes and adjusted >= config["agent_min_score"],
        "adjusted_score": round(clamp(adjusted), 1),
        "vetoes": list(dict.fromkeys(vetoes)),
    }


def allocation_stage(signal: dict, risk: dict, portfolio: dict, config: dict) -> dict:
    if not risk["approved_shadow"]:
        return {"action": "NO_ALLOCATION", "amount_gbp": 0.0, "reason": "risk judge did not approve"}
    headroom = portfolio["remaining_exposure_gbp"]
    quality_fraction = clamp((risk["adjusted_score"] - config["agent_min_score"]) / max(1, 100 - config["agent_min_score"]), 0.25, 1.0)
    amount = min(config["max_order_gbp_hard"], headroom) * quality_fraction
    return {
        "action": "SHADOW_PROPOSAL",
        "amount_gbp": round(max(0.0, amount), 2),
        "reason": "proposal only; existing bot retains preview/approval/execution authority",
    }


def evaluate_team(snapshot: dict, config: dict, lab_status: dict | None = None) -> dict:
    portfolio = portfolio_state(snapshot, config)
    rows = []
    for symbol, asset in (snapshot.get("assets") or {}).items():
        if not isinstance(asset, dict):
            continue
        signal = signal_stage(str(symbol), asset, snapshot, lab_status)
        bull = bull_stage(signal)
        bear = bear_stage(signal)
        risk = risk_judge(signal, bull, bear, portfolio, config)
        allocation = allocation_stage(signal, risk, portfolio, config)
        rows.append({"signal": signal, "bull": bull, "bear": bear, "risk": risk, "allocation": allocation})
    rows.sort(key=lambda r: r["risk"]["adjusted_score"], reverse=True)
    best = rows[0] if rows else None
    if not best:
        decision, reason = "NO_TRADE", "No assets were available for analysis."
    elif portfolio["open_positions"] >= portfolio["max_positions"]:
        decision, reason = "PORTFOLIO_FULL_REVIEW_ONLY", "Position ceiling is full."
    elif portfolio["remaining_exposure_gbp"] <= 0:
        decision, reason = "EXPOSURE_FULL_REVIEW_ONLY", "Exposure ceiling is full."
    elif best["risk"]["approved_shadow"]:
        decision, reason = "SHADOW_TRADE_READY", f"{best['signal']['symbol']} passed signal, debate and risk stages."
    elif best["risk"]["adjusted_score"] >= config["watch_min_score"]:
        decision, reason = "WATCH", f"{best['signal']['symbol']} is worth monitoring but has risk vetoes."
    else:
        decision, reason = "NO_TRADE", "No candidate clears the risk-adjusted threshold."
    return {
        "schema": "andys-bot-agentic-team-v2",
        "mode": "SHADOW_ONLY",
        "decision": decision,
        "decision_reason": reason,
        "portfolio": {k: v for k, v in portfolio.items() if k != "positions"},
        "best_candidate": best,
        "candidates": rows[:12],
        "guardrails": {
            "live_orders": False,
            "transfers": False,
            "risk_changes": False,
            "max_positions_hard": config["max_positions_hard"],
            "max_order_gbp_hard": config["max_order_gbp_hard"],
            "max_exposure_gbp_hard": config["max_exposure_gbp_hard"],
        },
    }
