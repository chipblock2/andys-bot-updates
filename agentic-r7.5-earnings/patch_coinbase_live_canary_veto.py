#!/usr/bin/env python3
"""Patch Andy's Bot live canary with the R7.5 AUTO-BUY audit/veto gate.

Risk-reducing only:
- never originates a candidate
- never increases size
- never submits/cancels/edits an order itself
- manual buy paths are unchanged
- covered AUTO BUY candidates require fresh SHADOW_READY + TAKER_NOW + taker PASS
- maker-PASS products fail closed if their expected R7.5 bridge row is missing
"""
from pathlib import Path

P=Path("coinbase_live_canary.py")
s=P.read_text(encoding="utf-8")

# Constants.
if "R75_STATUS_FILE =" not in s:
    anchor='FEE_OVERRIDE_FILE = BASE_DIR / "coinbase_fee_override.json"\n'
    insert=anchor+'''R75_STATUS_FILE = BASE_DIR / "r7_5_earnings_shadow" / "state" / "r7_5_live_shadow_status.json"
R75_MAKER_VALIDATION_FILE = BASE_DIR / "r7_5_earnings_shadow" / "state" / "strategy_lab_maker_status.json"
R75_EXECUTION_AUDIT_FILE = BASE_DIR / "r7_5_earnings_shadow" / "state" / "r7_5_live_execution_audit.jsonl"
'''
    if anchor not in s:
        raise SystemExit("fee constant anchor not found")
    s=s.replace(anchor,insert,1)

# Pure decision helper + best-effort audit writer.
if "def _r75_auto_buy_decision(" not in s:
    anchor='def _flag(perms: dict, key: str):\n'
    helper=r'''def _r75_auto_buy_decision(symbol: str) -> dict:
    """Pure R7.5 gate lookup. Never calls Coinbase or submits an order."""
    symbol=str(symbol or "").upper().replace("-GBP","")
    status=_load(R75_STATUS_FILE)
    product=f"{symbol}-GBP" if symbol else ""
    row=next((x for x in (status.get("candidates") or []) if str((x or {}).get("product") or "").upper()==product),None)
    try: age=max(0.0,time.time()-R75_STATUS_FILE.stat().st_mtime)
    except Exception: age=999999.0
    route=str(((row or {}).get("smart_execution") or {}).get("route") or "")
    validation=(row or {}).get("execution_validation") or {}
    gate={
        "covered":bool(row),"product":product,"state":(row or {}).get("state"),
        "route":route,"reasons":(row or {}).get("reasons") or [],
        "maker_verdict":((validation.get("maker") or {}).get("verdict")),
        "taker_verdict":((validation.get("taker") or {}).get("verdict")),
        "strategy":(row or {}).get("strategy"),
        "strategy_compatible":(row or {}).get("strategy_compatible"),
        "generated_utc":status.get("generated_utc"),"age_seconds":round(age,1),
    }
    if not row:
        maker_validation=_load(R75_MAKER_VALIDATION_FILE)
        validated_pass=any(
            str((r or {}).get("market") or "").upper()==product
            and str((r or {}).get("verdict") or "").upper()=="PASS"
            for r in (maker_validation.get("results") or [])
        )
        if validated_pass:
            gate.update({"covered_expected":True,"allowed":False,"reason":f"{product} has PASS validation but is missing from the fresh R7.5 bridge."})
        else:
            gate.update({"covered_expected":False,"allowed":True,"reason":"R7.5 has no PASS validation for this product; existing live gates remain authoritative."})
    elif age>180.0:
        gate.update({"allowed":False,"reason":f"R7.5 shadow status is stale ({age:.0f}s)."})
    elif str(row.get("state") or "").upper()!="SHADOW_READY":
        why=", ".join(str(x) for x in ((row.get("reasons") or [])[:3])) or str(row.get("state") or "not ready")
        gate.update({"allowed":False,"reason":f"{product} is not SHADOW_READY — {why}"})
    elif route!="TAKER_NOW":
        gate.update({"allowed":False,"reason":f"{product} route is {route or 'unknown'}, not TAKER_NOW."})
    elif str(((validation.get("taker") or {}).get("verdict")) or "").upper()!="PASS":
        gate.update({"allowed":False,"reason":f"{product} taker-fee walk-forward did not PASS."})
    else:
        gate.update({"allowed":True,"reason":"Fresh SHADOW_READY + TAKER_NOW + taker PASS."})
    return gate

def _r75_audit(event: str, gate: dict, **extra) -> None:
    try:
        R75_EXECUTION_AUDIT_FILE.parent.mkdir(parents=True,exist_ok=True)
        row={"utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),"event":str(event),**(gate or {}),**extra}
        with R75_EXECUTION_AUDIT_FILE.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,separators=(",",":"))+"\\n")
    except Exception:
        pass


'''
    if anchor not in s:
        raise SystemExit("helper insertion anchor not found")
    s=s.replace(anchor,helper+anchor,1)

# Replace the older inline veto if present.
old='''            r75_path=BASE_DIR/"r7_5_earnings_shadow"/"state"/"r7_5_live_shadow_status.json"
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
'''
new='''            r75_gate=_r75_auto_buy_decision(symbol)
            state["r75_auto_buy_gate"]=r75_gate;_save(STATE_FILE,state)
            if not r75_gate.get("allowed"):
                _r75_audit("BLOCK",r75_gate,symbol=symbol)
                raise RuntimeError("R7.5 VETO: "+str(r75_gate.get("reason") or "not allowed"))
            _r75_audit("ALLOW_PREVIEW",r75_gate,symbol=symbol)
'''
if old in s:
    s=s.replace(old,new,1)
elif 'r75_gate=_r75_auto_buy_decision(symbol)' not in s:
    anchor='''            if not self._qualified(symbol,row,settings): raise RuntimeError(f"{symbol} no longer clears the live gates.")
            ok70,p70,why70=profit_narrative_intelligence.auto_buy_gate(symbol,row,bool(state.get("profit_focus_enabled")))
'''
    replacement='''            if not self._qualified(symbol,row,settings): raise RuntimeError(f"{symbol} no longer clears the live gates.")
'''+new+'''            ok70,p70,why70=profit_narrative_intelligence.auto_buy_gate(symbol,row,bool(state.get("profit_focus_enabled")))
'''
    if anchor not in s:
        raise SystemExit("AUTO BUY insertion anchor not found")
    s=s.replace(anchor,replacement,1)

# Surface last gate in /api/live.
if '"r7_5_auto_buy_gate": state.get("r75_auto_buy_gate") or {}' not in s:
    anchor='''            "auto_buy_enable_block_reason": auto_buy_enable_block_reason,
            "profit_focus_enabled": bool(state.get("profit_focus_enabled")),
'''
    replacement='''            "auto_buy_enable_block_reason": auto_buy_enable_block_reason,
            "r7_5_auto_buy_gate": state.get("r75_auto_buy_gate") or {},
            "profit_focus_enabled": bool(state.get("profit_focus_enabled")),
'''
    if anchor not in s:
        raise SystemExit("public-status anchor not found")
    s=s.replace(anchor,replacement,1)

P.write_text(s,encoding="utf-8")
print("R7.5 audit/veto gate patch applied")
