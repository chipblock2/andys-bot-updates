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
