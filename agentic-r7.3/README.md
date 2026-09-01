# Andy's Bot R7.3 — Agentic Companion

Safe read-only/shadow companion for the installed R7.2.1 build.

## Adds
- 5-minute opportunity scan
- hourly deep review
- 0–100 Agentic ranking using existing Decision Council, calibrated probability, after-cost edge, MTF evidence, market activity/location, per-coin edge, news, market quality and read-only derivatives/perp context
- explicit `NO_TRADE`
- live-position re-score: `HOLD`, `PROTECT`, `REVIEW_EXIT` (advice only)
- portfolio-full/exposure-full states that never force another position
- JSONL audit trail and local health/status dashboard

## Forced guardrails
The companion has no live-order, transfer or risk-change capability. The code forces `SHADOW_ONLY` and clamps recommendation ceilings to 8 positions, £10/order and £20 total exposure. The existing Andy's Bot remains authoritative for all actual live controls and local preview/approval.

## Install
Use the packaged `Install_R7_3_Agentic_Upgrade.ps1`. It installs beside R7.2.1 and creates a desktop shortcut. The local dashboard is `http://127.0.0.1:8793`.

The main `manifest.json` is intentionally unchanged because it currently advertises the older R5.8.2 updater proof package; forcing this companion through that manifest could regress a machine already running R7.2.1.
