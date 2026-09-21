# Andy's Bot R7.5 Earnings Engine

R7.5 is a shadow-only earnings/risk policy layer designed to improve net return per trade, not trade frequency.

It adds:
- Strategy health gating from walk-forward PF, drawdown, fold consistency, parameter stability and recent unseen folds.
- Regime routing so breakout/trend/mean-reversion logic is only considered in compatible markets.
- Account-specific fee support from Coinbase Advanced GET /api/v3/brokerage/transaction_summary.
- Fee, slippage and safety-buffer net-edge gating.
- Spread, order-book depth and market-status liquidity gating.
- Adaptive sizing based on signal quality, health, regime, liquidity and net edge.
- Maker-first POST_ONLY_LIMIT proposals with bounded repricing and cancel-on-timeout.
- No automatic taker fallback by default.
- Existing hard ceilings remain 8 positions, GBP10/order and GBP20 total exposure.

Current ETH breakout:
The R7.4 real walk-forward scan passed overall, but its last two unseen folds were negative. R7.5 therefore holds it at WATCH rather than READY until newer evidence improves.

Safety:
This package cannot place orders, move funds, change risk limits or bypass the existing preview/approval layer.

Test with: python self_test.py
Expected: R7.5 SELF-TEST PASS

Additional R7.5 profit protection:
- Fee-aware break-even recommendation after 1.0R.
- ATR trailing recommendation after 1.5R.
- Existing stops can only tighten; the policy never loosens protection.
- Protective exits are costed conservatively using taker fees.
- Partial-profit splitting remains disabled until it is separately validated.

Account-fee rule:
R7.5 will not mark a candidate SHADOW_READY when it only has fallback fee assumptions. It requires account-specific Coinbase fee-tier data before readiness.


## Studio live-shadow deployment
The Studio bot now runs a separate R7.5 read-only bridge against the existing local /api/live endpoint on port 8787. The bridge inherits the bot's current supervised live limits instead of overwriting them.

Observed deployment configuration on 2026-09-21:
- Live mode: GBP100 supervised
- Live order cap: GBP15
- Live exposure cap: GBP100
- Max live positions: 8
- Coinbase authenticated fee profile: VIP 1, 0.06% maker / 0.16% taker at the time observed

The bridge consumes existing Coinbase L2 order-book fields, fee_profile, live_canary and model decisions. It cannot place, approve, cancel or modify live orders.

A real-fee walk-forward rerun using 0.06% maker fees produced:
- ETH-GBP breakout: PASS, +22.8%, PF 1.85, 13.1% max drawdown
- ETH-GBP trend: PASS, +17.4%, PF 1.31, 14.2% max drawdown
- BTC-GBP breakout: PASS, +13.9%, PF 1.40, 11.5% max drawdown

Current live-engine decisions remain authoritative; R7.5 will not create a trade when the base engine is BLOCKED/HOLD.
