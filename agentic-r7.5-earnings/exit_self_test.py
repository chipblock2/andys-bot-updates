#!/usr/bin/env python3
import json
from pathlib import Path
from exit_policy import recommend_stop

cfg = json.loads((Path(__file__).resolve().parent / "config.json").read_text())

r = recommend_stop(
    entry=100, current=107, highest=108, atr=1.2,
    current_stop=96, initial_stop=95,
    maker_fee=0.0025, taker_fee=0.006,
    config=cfg,
)
assert r["action"] == "TIGHTEN_STOP", r
assert r["stop"] >= r["fee_aware_break_even"], r
assert r["stop"] >= 96, r

r2 = recommend_stop(
    entry=100, current=107, highest=108, atr=1.2,
    current_stop=106, initial_stop=95,
    maker_fee=0.0025, taker_fee=0.006,
    config=cfg,
)
assert r2["stop"] >= 106, r2

print("R7.5 EXIT SELF-TEST PASS")
print(r)
