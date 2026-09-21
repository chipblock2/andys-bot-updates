# Execution promotion guard

R7.5 must not promote a route into wider live execution merely because a few recent examples looked good.

Current shadow requirements:
- Candidate observations must be SHADOW_READY.
- Minimum 100 completed observations.
- At least 55% positive 15-minute outcomes.
- Average taker outcome at least +0.05%.
- MAKER_WAIT additionally requires at least 15% maker fill rate.

At the time of introduction:
- NO_TRADE / WATCH: 126 samples, 19.0% positive, -0.517% average.
- WAIT_RETEST / WATCH: 140 samples, 25.0% positive, -0.395% average.
- TAKER_NOW / WATCH: 30 samples, 50.0% positive, -0.166% average.

No route is promotion-ready. This guard is shadow-only and cannot change live execution.
