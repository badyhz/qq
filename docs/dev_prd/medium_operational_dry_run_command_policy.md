# Medium Operational Dry-Run Command Policy (T1272)

## Purpose

Define command safety rules for the 13 medium-risk untracked
operational scripts. All commands must be safe for dry-run execution.

## release_hold = HOLD

No command defined here may be executed in live mode.

## Policy

### P1: No live order commands

Scripts must NOT contain commands that submit orders to any exchange.
Permitted patterns:

- `dry_run=True`
- `mode=dry-run`
- `simulate=True`
- `testnet=True` (with no real funds)

### P2: No shell=True

Scripts must NOT use `subprocess.run(..., shell=True)` or equivalent.
All subprocess calls must use argument lists.

### P3: No eval/exec

Scripts must NOT use `eval()`, `exec()`, or `compile()` on
untrusted input.

### P4: No destructive CLI flags

Scripts must NOT pass flags that cause:

- Account wipe
- Position close
- Fund transfer
- API key rotation

### P5: Command logging

Every command executed by the script must be logged with:

- Timestamp
- Command string
- Exit code
- Dry-run indicator

## Enforcement

- Review checklist T1279 includes command safety checks.
- Pre-commit hooks must reject scripts violating P1-P4.
