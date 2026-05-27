# Medium Operational Deny-Submit Policy (T1275)

## Purpose

Define the absolute prohibition on live order submission for the
13 medium-risk untracked operational scripts. No script in this
batch may submit orders to any exchange under any condition.

## release_hold = HOLD

The deny-submit invariant holds regardless of hold state. Even
after hold release, these scripts require explicit human approval
for any submission capability.

## Policy

### P1: No exchange client instantiation

Scripts must NOT create exchange client objects that connect to
live exchange endpoints. Permitted:

- Mock clients
- Testnet clients (with no real funds)
- Dry-run adapters

### P2: No order submission calls

Scripts must NOT call methods that result in order placement:

- `create_order()`
- `submit_order()`
- `place_order()`
- Any equivalent exchange API call

### P3: No conditional bypass

Scripts must NOT contain code paths that conditionally enable
live submission based on:

- Environment variables (unless gated by human approval)
- File existence checks
- Time-based conditions
- Network availability

### P4: Kill switch requirement

Any script that interacts with order-like data structures must
implement a kill switch that:

- Defaults to ON (killed)
- Requires explicit human action to disable
- Logs all state transitions

### P5: Submission audit trail

If a script ever receives future approval for submission, it must:

- Log every submission attempt
- Include dry-run/simulation tag
- Write to `evidence/` directory
- Notify human reviewer

## Enforcement

- Pre-commit hook: reject scripts containing P1-P3 violations.
- Review checklist T1279 includes deny-submit checks.
- Any violation is a BLOCKER for promotion.
