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


## Expanded altcoin validation

Maker 0.06%:
- DOGE-GBP breakout: +48.5%, PF 2.47, 11.2% max DD — PASS
- ALGO-GBP breakout: +35.7%, PF 2.36, 12.0% max DD — PASS
- DOGE-GBP trend: +24.7%, PF 1.48 — PASS
- SOL-GBP breakout: +21.4%, PF 2.06, 10.4% max DD — PASS
- ADA-GBP breakout: +19.5%, PF 1.98, 8.7% max DD — PASS
- CRV-GBP breakout: +19.2%, PF 1.48, 24.3% max DD — PASS
- UNI-GBP breakout: +18.3%, PF 1.53, 9.5% max DD — PASS
- SOL-GBP trend: +16.5%, PF 1.30 — PASS
- LINK-GBP trend: +16.4%, PF 1.23 — PASS
- CRV-GBP meanrev: +3.9%, PF 1.43 — PASS

Taker 0.16%:
- DOGE-GBP breakout: +45.6%, PF 2.34 — PASS
- ALGO-GBP breakout: +33.1%, PF 2.20 — PASS
- SOL-GBP breakout: +19.4%, PF 1.92 — PASS
- ADA-GBP breakout: +18.0%, PF 1.88 — PASS
- DOGE-GBP trend: +17.0%, PF 1.28 — PASS
- UNI-GBP breakout: +15.7%, PF 1.43 — PASS
- SOL-GBP trend: +12.8%, PF 1.21 — PASS
- CRV-GBP meanrev: +2.8%, PF 1.30 — PASS

Notable route split:
- CRV breakout PASSes maker validation but FAILs taker validation.
- LINK trend PASSes maker validation but FAILs taker validation.
- LTC breakout/trend/mean-reversion all FAIL despite a recent profitable live LTC trade.

R7.5 dynamically discovers maker-PASS strategies from the validation file, but a TAKER_NOW route still requires the same market/strategy to PASS the taker validation file.
