# Phase 10M: Shadow Operation Runbook / Daily Operator Commands

## Summary

Created operator runbook and status helper for daily shadow trading operations.

## Files Added

- `docs/SHADOW_TRADING_DAILY_OPERATOR_RUNBOOK.md` — daily operator guide
- `scripts/print_shadow_operator_status.py` — status summary from latest reports
- `tests/unit/test_print_shadow_operator_status_script.py` — 27 tests
- `docs/PHASE10M_SHADOW_OPERATION_RUNBOOK_RESULT.md` — this file

## What the Runbook Covers

1. System boundary (paper-only, shadow-only, no order, no testnet, no live)
2. Daily commands for:
   - Discovering new opportunities (full lifecycle)
   - Managing existing positions only (update-only pipeline)
   - Offline checking
   - Status check
3. Report file locations
4. Status field explanations
5. When to continue shadow collection
6. Human review gate (never auto testnet/live)
7. Common mistakes to avoid
8. Recommended daily rhythm
9. Safety checklist
10. File inventory

## Status Helper

`scripts/print_shadow_operator_status.py` reads:
- `*_shadow_sample_gate.json` → sample_status, testnet_gate_status
- `*_paper_performance_scorecard.json` → clean/closed positions, win rate
- `*_paper_positions_quarantine.json` → excluded counts

Output: human-readable status with next-action guidance.

## Safety

- No strategy changes
- No signal logic changes
- No paper position logic changes
- No testnet/live/order
- No .env / os.environ / os.getenv
- No websocket
- No daemon / background runner
- Read-only from reports

## Daily Commands

```bash
# Full lifecycle (discover + update)
python3 scripts/run_shadow_trading_lifecycle.py --allow-public-http
python3 scripts/run_sample_collection_gate.py

# Update-only (manage existing positions)
python3 scripts/run_shadow_position_update_only.py --allow-public-http
python3 scripts/run_sample_collection_gate.py

# Status check
python3 scripts/print_shadow_operator_status.py
```

## Commit Plan

```bash
git add docs/SHADOW_TRADING_DAILY_OPERATOR_RUNBOOK.md
git commit -m "Add shadow trading daily operator runbook"

git add scripts/print_shadow_operator_status.py tests/unit/test_print_shadow_operator_status_script.py
git commit -m "Add shadow operator status helper"

git add docs/PHASE10M_SHADOW_OPERATION_RUNBOOK_RESULT.md
git commit -m "Document shadow operation runbook"
```
