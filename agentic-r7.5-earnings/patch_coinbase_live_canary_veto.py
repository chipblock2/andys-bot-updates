#!/usr/bin/env python3
"""Patch Andy's Bot live canary with the R7.5 AUTO-BUY veto.

Veto-only: R7.5 cannot originate a trade, increase size, or affect manual buys.
Covered symbols are blocked from AUTO BUY unless fresh R7.5 state is SHADOW_READY.
"""
from pathlib import Path
P=Path("coinbase_live_canary.py")
s=P.read_text(encoding="utf-8")
anchor='''            if not self._qualified(symbol,row,settings): raise RuntimeError(f"{symbol} no longer clears the live gates.")
            ok70,p70,why70=profit_narrative_intelligence.auto_buy_gate(symbol,row,bool(state.get("profit_focus_enabled")))
'''
insert='''            if not self._qualified(symbol,row,settings): raise RuntimeError(f"{symbol} no longer clears the live gates.")
            r75_path=BASE_DIR/"r7_5_earnings_shadow"/"state"/"r7_5_live_shadow_status.json"
            r75_status=_load(r75_path)
            r75=next((x for x in (r75_status.get("candidates") or []) if str((x or {}).get("product") or "").upper()==f"{symbol}-GBP"),None)
            r75_gate={"covered":bool(r75),"product":f"{symbol}-GBP","state":(r75 or {}).get("state"),"reasons":(r75 or {}).get("reasons") or [],"generated_utc":r75_status.get("generated_utc")}
            state["r75_auto_buy_gate"]=r75_gate;_save(STATE_FILE,state)
            if r75:
                try: r75_age=max(0.0,time.time()-r75_path.stat().st_mtime)
                except Exception: r75_age=999999.0
                if r75_age>180.0: raise RuntimeError(f"R7.5 VETO: {symbol} shadow status is stale ({r75_age:.0f}s).")
                if str(r75.get("state") or "").upper()!="SHADOW_READY":
                    why=", ".join(str(x) for x in ((r75.get("reasons") or [])[:3])) or str(r75.get("state") or "not ready")
                    raise RuntimeError(f"R7.5 VETO: {symbol} is not shadow-ready — {why}")
            ok70,p70,why70=profit_narrative_intelligence.auto_buy_gate(symbol,row,bool(state.get("profit_focus_enabled")))
'''
anchor2='''            "auto_buy_enable_block_reason": auto_buy_enable_block_reason,
            "profit_focus_enabled": bool(state.get("profit_focus_enabled")),
'''
insert2='''            "auto_buy_enable_block_reason": auto_buy_enable_block_reason,
            "r7_5_auto_buy_gate": state.get("r75_auto_buy_gate") or {},
            "profit_focus_enabled": bool(state.get("profit_focus_enabled")),
'''
if anchor not in s: raise SystemExit("AUTO BUY anchor not found")
if anchor2 not in s: raise SystemExit("public-status anchor not found")
P.write_text(s.replace(anchor,insert,1).replace(anchor2,insert2,1),encoding="utf-8")
print("R7.5 AUTO-BUY veto patch applied")
