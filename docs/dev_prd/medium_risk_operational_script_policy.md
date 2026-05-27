# Medium-Risk Operational Script Policy (T1172)

## Purpose

Define mandatory rules for medium-risk operational scripts.

## Rules

### R1: Must be dry-run default

Every operational script must default to dry-run mode. No real orders,
no real network calls to exchange endpoints, no mutations to live state.

### R2: Must not auto-commit

Operational scripts must never call `git add`, `git commit`, or any
equivalent. Commits are a separate human-reviewed step.

### R3: Must log all actions

Every action taken by the script must be logged. Log destinations:

- stdout (for interactive use)
- `logs/` directory (for audit trail)

Log entries must include: timestamp, action type, target, outcome.

## Enforcement

- Pre-commit hook: reject commits that include operational scripts
  violating these rules.
- Review checklist: T1179 promotion checklist includes these checks.
