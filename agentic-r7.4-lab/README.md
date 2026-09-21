# Andy's Bot R7.4 Lab + Agentic Supervisor

This package is designed to run beside the existing bot. It does not replace the live engine and contains no live-order endpoint.

## Added from Strategy Lab v2
- Coinbase candle cache
- trend / breakout / mean-reversion families
- parameter grids
- walk-forward selection on past data and scoring on unseen folds
- fee + slippage assumptions
- next-candle fills
- ATR trailing stops
- risk-based sizing
- drawdown halt/flatten in paper mode
- CSV ledgers
- machine-readable validation status
- optional Telegram paper alerts

## Added from the OctoBot review (reimplemented, not copied verbatim)
- staged Signal -> Bull/Bear -> Risk Judge -> Distribution architecture
- independent portfolio concentration/exposure checks
- explicit risk vetoes
- allocation proposal separated from signal generation
- strategy-validation evidence included as a separate component
- shadow-only supervisor boundary

## Safety / integration
The existing bot remains authoritative for preview, approval, execution, positions and risk controls. R7.4 only proposes shadow allocations. Hard caps remain 8 positions, GBP10/order and GBP20 exposure until the live engine is deliberately changed.

## Test
python andys_strategy_lab.py scan --synthetic

Synthetic results only test the software path. They are not evidence that a strategy is profitable.
