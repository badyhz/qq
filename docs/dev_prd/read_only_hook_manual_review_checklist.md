# Read-Only Hook Manual Review Checklist

## Purpose

Define the checklist for manual review of any read-only hook before it is registered or modified. Every item MUST be verified by a human reviewer.

## Contract

```yaml
checklist:
  items: list
  required: all
  reviewer: human
```

## Fields / Items

### Checklist Items

| # | Item | Verification Method | Pass Criteria |
|---|---|---|---|
| 1 | Permissions verified | Review permission adapter output | Only read-only flags granted; no write flags; FROZEN logic correct |
| 2 | Invariants pass | Review invariant_results in evidence | All invariants in the declared set have `passed: true` |
| 3 | No side effects | Review proof packet verdict | Verdict is `PROVEN`; static analysis and runtime assertions both clean |
| 4 | Sanitized output | Review sanitized_output field | No secrets, credentials, API keys, account state, or live data present |
| 5 | Evidence complete | Review evidence_record | All fields present; timestamp from context; invariants_checked matches declared set |
| 6 | No live paths | Review import graph in proof packet | No imports of live trading modules, execution modules, or order managers |
| 7 | No secrets in input | Review input payload | No fields matching sanitized field patterns present in raw input |
| 8 | Deterministic output | Review regression packet | Verdict is `MATCH` when run against baseline with same input |
| 9 | Failure handling | Review failure taxonomy coverage | All failure categories handled; no uncaught exceptions; `UNKNOWN` only as last resort |
| 10 | Documentation | Review this design doc set | All 10 design contracts present, consistent, and up to date |

### Review Process

1. Reviewer reads the hook source code.
2. Reviewer runs the hook against test fixtures.
3. Reviewer inspects the proof packet.
4. Reviewer inspects the evidence record.
5. Reviewer inspects the regression packet against baseline.
6. Reviewer checks each checklist item.
7. Reviewer signs off with `REVIEWED` status and date.

## Rules

1. All items are required. No item is optional.
2. Reviewer MUST be a human; automated checks are supplementary.
3. Review is required before initial registration and before any modification.
4. Review results are recorded in the hook's evidence store.
5. Failed review blocks hook registration.

## Safety

- Review checklist itself has no side effects.
- Checklist does not access live trading systems.
- Checklist is a reference document, not executable code.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
