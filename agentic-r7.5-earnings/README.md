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
