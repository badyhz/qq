# T837 — Runtime Governance Read-Only Blocker Summary

## Purpose

Summarize blockers for the read-only governance layer. Combines dangerous permission evaluations (T834) and invariant failures (T832) into a single actionable summary.

## Dataclass

`RuntimeGovernanceReadOnlyBlockerSummary` (frozen=True):

| Field | Type | Description |
|---|---|---|
| `total_blockers` | `int` | Sum of permission + invariant blockers |
| `dangerous_permission_blockers` | `int` | Evaluations where `actual_verdict=="BLOCKED"` |
| `invariant_blockers` | `int` | `invariant_summary.get("failed", 0)` |
| `recommended_action` | `str` | `PROCEED` / `REVIEW` / `BLOCK` |
| `notes` | `List[str]` | Human-readable blocker notes |

## Functions

### `summarize_readonly_blockers(evaluations=None, invariant_summary=None) -> RuntimeGovernanceReadOnlyBlockerSummary`

Pure. Deterministic. No I/O. No timestamps. No random.

**Decision logic:**
- `BLOCK` if `dangerous_permission_blockers > 0` or `invariant_blockers > 0`
- `REVIEW` if `total_blockers > 0`
- `PROCEED` if `total_blockers == 0`

**Defaults (no args):** all counts zero, action `PROCEED`.

### `readonly_blocker_summary_to_dict(summary) -> Dict`

Serialize to dict with keys: `total_blockers`, `dangerous_permission_blockers`, `invariant_blockers`, `recommended_action`, `notes`.

### `readonly_blocker_summary_to_markdown(summary) -> str`

Deterministic markdown. No timestamps. Includes counts, action, and notes section when present.

## Dependencies

- T834 `RuntimeGovernanceReadOnlyScenarioEvaluation` — provides `actual_verdict` field
- T832 `summarize_readonly_invariants` — provides `{"failed": int}` dict
