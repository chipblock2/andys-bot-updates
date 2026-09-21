#!/usr/bin/env python3
import json
from pathlib import Path
from earnings_engine import evaluate_earnings_candidate, strategy_health

ROOT = Path(__file__).resolve().parent
cfg = json.loads((ROOT / "config.json").read_text())

lab = {
    "results": [{
        "market": "ETH-GBP",
        "strategy": "breakout",
        "verdict": "PASS",
        "metrics": {
            "pf": 1.62, "mdd": 0.1466, "positive_folds": 2,
            "folds": 4, "param_stability": 1.0
        },
        "fold_stats": [
            {"return": 0.0438}, {"return": 0.2192},
            {"return": -0.0638}, {"return": -0.0156}
        ],
    }]
}
asset = {
    "multi_timeframe": {"score": 42},
    "market_opportunity": {"activity_score": 76, "chase_risk": False},
}
snapshot = {"btc_regime_breadth": {"btc": {"state": "NORMAL"}, "breadth": {"state": "HEALTHY"}}}
book = {
    "best_bid": 3000.0, "best_ask": 3001.5,
    "bid_depth_gbp": 1000.0, "ask_depth_gbp": 1200.0,
    "market_status": "FULL_TRADING",
}
fees = {"fee_tier": {"maker_fee_rate": "0.0025", "taker_fee_rate": "0.006"}}
portfolio = {"remaining_exposure_gbp": 20.0}

h = strategy_health(lab, "ETH-GBP", "breakout", cfg)
assert h["state"] == "WATCH", h

candidate = evaluate_earnings_candidate(
    product="ETH-GBP", strategy="breakout", signal_score=86,
    expected_return=0.025, asset=asset, snapshot=snapshot,
    lab_status=lab, book=book, fee_summary=fees,
    portfolio=portfolio, config=cfg,
)
assert candidate["state"] == "WATCH", candidate
assert candidate["execution"]["action"] == "NO_ORDER", candidate

lab["results"][0]["fold_stats"][-2:] = [{"return": 0.03}, {"return": 0.02}]
candidate2 = evaluate_earnings_candidate(
    product="ETH-GBP", strategy="breakout", signal_score=90,
    expected_return=0.03, asset=asset, snapshot=snapshot,
    lab_status=lab, book=book, fee_summary=fees,
    portfolio=portfolio, config=cfg,
)
assert candidate2["state"] == "SHADOW_READY", candidate2
assert 0 < candidate2["sizing"]["amount_gbp"] <= 10
assert candidate2["execution"]["post_only"] is True
assert candidate2["execution"]["taker_fallback_allowed"] is False

bad_book = dict(book, best_ask=3010.0)
candidate3 = evaluate_earnings_candidate(
    product="ETH-GBP", strategy="breakout", signal_score=95,
    expected_return=0.04, asset=asset, snapshot=snapshot,
    lab_status=lab, book=bad_book, fee_summary=fees,
    portfolio=portfolio, config=cfg,
)
assert candidate3["state"] != "SHADOW_READY"
assert not candidate3["liquidity"]["allowed"]

print("R7.5 SELF-TEST PASS")
print("current ETH breakout health:", h)
print("healthy shadow proposal:", candidate2["sizing"], candidate2["execution"])
