# R7.5 live integration

Validated on the Studio bot on 21 September 2026.

## Live behaviour
- R7.5 is veto-only for AUTO BUY.
- It never creates a candidate, increases size, or affects manual buys.
- Covered symbols require fresh SHADOW_READY state.
- Uncovered symbols remain governed by the existing live gates.
- Existing Coinbase stop/target protection is unchanged.

## Live fee tier observed
VIP 1: maker 0.06%, taker 0.16%.

## Walk-forward at the live maker fee
- ETH-GBP breakout: +22.8%, PF 1.85, 13.1% max DD, PASS.
- ETH-GBP trend: +17.4%, PF 1.31, 14.2% max DD, PASS.
- BTC-GBP breakout: +13.9%, PF 1.40, 11.5% max DD, PASS.

## Maker-first validation
A Coinbase PREVIEW ONLY request using limit_limit_gtc, post_only=true and attached TP/SL was accepted for ETH-GBP. No order was submitted.

Do not switch live entries wholesale to maker-only yet. The existing queue-aware market-maker paper lab showed 20 bid fills from 308 quote episodes (~6.5% fill incidence) and negative paper P/L, so timeout/reprice behaviour needs more evidence.

## Windows reliability
live_shadow_bridge.py includes a PermissionError fallback for status JSON writes when Windows/AV temporarily blocks atomic replace.


## Smart execution research
R7.5 now adds a shadow execution selector:
- NO_TRADE when the candidate is not SHADOW_READY.
- WAIT_RETEST when entry is extended/chase-risk.
- TAKER_NOW only when immediate net edge and urgency clear the route thresholds.
- MAKER_WAIT only when maker edge is positive and the estimated maker-fill probability is high enough.

The selector uses the existing queue-aware market-maker lab as empirical fill evidence. At the time of integration that lab had 20 bid fills from 308 quote episodes (~6.5%), so live maker-only entry remains disabled.

TAKER_NOW is additionally required to PASS the taker-fee walk-forward validation.

## Counterfactual learner
execution_counterfactual.py runs shadow-only. It compares hypothetical immediate taker entry against a hypothetical maker bid and marks both to a later bid. It never contacts an order endpoint.

## Exit advisor
exit_advisor.py tracks live positions and public Coinbase candles, then applies fee-aware break-even and ATR trailing logic. It is advisory only and cannot edit the Coinbase bracket. On 21 September 2026 it recommended a tighter shadow stop for SOL while the actual exchange stop remained unchanged.

## Reliability
start_r75_shadow.ps1 now idempotently starts:
- live_shadow_bridge.py
- execution_counterfactual.py
- exit_advisor.py

A five-minute Windows watchdog re-runs that start script. A separate daily 03:15 task refreshes maker and taker walk-forward validation files.


## Dynamic validation universe
The daily fee-validation refresh now covers:
BTC, ETH, DOT, SOL, ADA, UNI, DOGE, CRV, ALGO, LTC, ATOM, LINK and AAVE GBP markets.

The live shadow bridge no longer hard-codes only BTC/ETH. It dynamically loads maker-PASS market/strategy pairs and applies strategy-family compatibility:
- breakout -> live MOMENTUM/SWING_TREND/MEME_RETEST + breakout location
- trend -> live MOMENTUM/SWING_TREND
- meanrev -> live MEAN_REVERSION/FAIR_VALUE_REVERSION

This prevents an unrelated historical strategy family from approving a live signal.

## Exit-price reliability fix
Held symbols can be absent from the model assets list. Exit advisor/counterfactual pricing therefore uses Coinbase public ticker data directly, with winner-watch/model price only as fallback. When model ATR is absent, the advisor calculates a public 1-hour ATR. Invalid pre-fix shadow state is diagnostic-only and was reset; no Coinbase order was modified.
