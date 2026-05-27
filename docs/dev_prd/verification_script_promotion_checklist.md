# Verification Script Promotion Checklist

**Task ID:** T1288
**release_hold:** HOLD
**Status:** Active

## Policy

A verification script is eligible for promotion only when ALL checklist items pass.

## Promotion Checklist

- [ ] T1282: High-risk imports absent or gated
- [ ] T1283: Dry-run-only proof documented
- [ ] T1284: All external dependencies mocked
- [ ] T1285: No side effects confirmed (pre/post diff clean)
- [ ] T1286: Regression tests exist and pass (>= 80% coverage)
- [ ] T1287: Human reviewer signed off with explicit approval
- [ ] Script has descriptive docstring explaining its purpose
- [ ] Script exits with code 0 on success, non-zero on failure
- [ ] Script output is human-readable and actionable
- [ ] release_hold = HOLD confirmed throughout

## Promotion States

| State | Condition |
|-------|-----------|
| DRAFT | Script written, not reviewed |
| REVIEWING | Under active review |
| APPROVED | All checklist items pass |
| PROMOTED | Merged to main |
| BLOCKED | One or more items fail |

## Current Scripts

| Script | State |
|--------|-------|
| verify_risk_release_flow.py | DRAFT |
| verify_testnet_repair_scenarios.py | DRAFT |
