# Runtime Governance Audit Event Model

**T796 — Pure audit event objects for runtime governance decisions.**

## Purpose

Provide deterministic, immutable audit event objects that record runtime governance decisions. No file I/O, no network calls, no live system dependencies.

## Data Model

### RuntimeGovernanceAuditEvent

Frozen dataclass with:

| Field | Type | Description |
|-------|------|-------------|
| event_id | str | Deterministic 16-char hex hash |
| run_id | str | Run identifier |
| adapter_id | str | Adapter identifier |
| action | str | Action being governed |
| verdict | str | Governance verdict (blocked, allowed, etc.) |
| failure_count | int | Number of failures |
| categories | List[str] | Sorted failure category values |
| severities | List[str] | Sorted failure severity values |
| metadata | Dict[str, Any] | Additional context |

### Event ID Determinism

`event_id` is a SHA-256 hash truncated to 16 hex chars, computed from:
- run_id
- adapter_id
- action
- verdict
- sorted categories
- sorted severities

No timestamps. No random values. Same inputs always produce same ID.

## Functions

### build_runtime_governance_audit_event(...)

Factory function. Accepts keyword arguments:

- `run_id: str`
- `adapter_id: str`
- `action: str`
- `verdict: str`
- `failures: List[GovernanceFailure] | None`
- `metadata: Dict[str, Any] | None`

Returns `RuntimeGovernanceAuditEvent`.

### audit_event_to_dict(event)

Serialize to plain dict. Returns a copy (safe to mutate).

### audit_event_to_markdown(event)

Deterministic markdown rendering. No timestamps. Metadata keys sorted.

## Imports

- `core.governance_failure_taxonomy.FailureCategory`
- `core.governance_failure_taxonomy.FailureSeverity`
- `core.governance_failure_taxonomy.GovernanceFailure`
