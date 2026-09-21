# R7.5 fee-specific validation

Observed Coinbase tier on the Studio bot: VIP 1.
- Maker: 0.06% per side
- Taker: 0.16% per side

## Maker-fee walk-forward
| Market | Strategy | Return | PF | Max DD | Verdict |
|---|---|---:|---:|---:|---|
| ETH-GBP | breakout | +22.8% | 1.85 | 13.1% | PASS |
| ETH-GBP | trend | +17.4% | 1.31 | 14.2% | PASS |
| BTC-GBP | breakout | +13.9% | 1.40 | 11.5% | PASS |
| BTC-GBP | trend | +1.6% | 0.93 | 15.6% | FAIL |

## Taker-fee walk-forward
| Market | Strategy | Return | PF | Max DD | Verdict |
|---|---|---:|---:|---:|---|
| ETH-GBP | breakout | +20.3% | 1.72 | 13.9% | PASS |
| BTC-GBP | breakout | +9.1% | 1.22 | 12.7% | PASS |
| ETH-GBP | trend | +10.3% | 1.13 | 18.1% | FAIL |

R7.5 therefore requires a TAKER_NOW route to also PASS the taker-fee walk-forward file.
A maker PASS cannot by itself justify immediate taker execution.

Mean-reversion remained FAIL on BTC and ETH and should stay disabled for these markets.
