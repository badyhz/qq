# Frozen Backlog Report Diff System (T1683)

## Purpose

Compare two frozen backlog report snapshots to identify changes in review status, approval evidence, and inventory composition over time.

## Scope

- Pure documentation and specification only
- No runtime execution, no exchange connectors, no secret management
- Release hold: HOLD

## Diff Model

A diff compares snapshot A (older) against snapshot B (newer) and produces a structured change report.

### Diff Output Fields

| Field | Type | Description |
|-------|------|-------------|
| diff_id | str | Unique identifier |
| snapshot_a_id | str | Source snapshot |
| snapshot_b_id | str | Target snapshot |
| generated_at | str | ISO 8601 timestamp |
| file_changes | list[FileChange] | Per-file change records |
| status_transitions | list[StatusTransition] | Review status changes |
| new_approvals | list[ApprovalEvidence] | Newly added approvals |
| inventory_changes | InventoryDelta | Added/removed files |

### FileChange

| Field | Type | Description |
|-------|------|-------------|
| path | str | File path |
| field | str | Changed field name |
| old_value | str | Value in snapshot A |
| new_value | str | Value in snapshot B |

### StatusTransition

| Field | Type | Description |
|-------|------|-------------|
| path | str | File path |
| from_status | str | Previous status |
| to_status | str | New status |
| timestamp | str | When transition occurred |

### InventoryDelta

| Field | Type | Description |
|-------|------|-------------|
| added | list[str] | Files added to inventory |
| removed | list[str] | Files removed from inventory |

## Diff Rules

1. Only forward transitions are valid (pending -> reviewed -> approved/rejected)
2. Reverse transitions (approved -> pending) require human justification
3. Inventory removals require human approval
4. New approvals must have complete ApprovalEvidence

## Acceptance Command

```bash
python3 -m pytest tests/unit/test_t1681_t1800_compatibility.py -v --tb=short
```

## Risk Level

Low — documentation and specification only.

## Dependencies

- T1682 (frozen backlog report snapshot)
- T1681 (frozen backlog report validator)
