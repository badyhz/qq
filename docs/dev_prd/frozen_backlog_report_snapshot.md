# Frozen Backlog Report Snapshot System (T1682)

## Purpose

Capture point-in-time snapshots of frozen backlog review state for diff comparison, audit trail, and regression detection.

## Scope

- Pure documentation and specification only
- No runtime execution, no exchange connectors, no secret management
- Release hold: HOLD

## Snapshot Model

A snapshot captures the complete frozen backlog review state at a specific timestamp.

### Snapshot Fields

| Field | Type | Description |
|-------|------|-------------|
| snapshot_id | str | Unique identifier (ISO timestamp + hash) |
| captured_at | str | ISO 8601 timestamp |
| frozen_file_inventory | list[FrozenFileEntry] | All HIGH-risk frozen files |
| governed_file_inventory | list[GovernedFileEntry] | All MEDIUM-risk governed files |
| review_statuses | dict[str, str] | file path -> review status |
| approval_evidence | list[ApprovalEvidence] | Human approval records |
| release_hold | str | Always "HOLD" unless human override |

### FrozenFileEntry

| Field | Type | Description |
|-------|------|-------------|
| path | str | Relative file path |
| risk_level | str | "HIGH" |
| frozen_since | str | ISO 8601 date when frozen |
| review_status | str | pending / reviewed / approved / rejected |

### ApprovalEvidence

| Field | Type | Description |
|-------|------|-------------|
| reviewer | str | Reviewer identity |
| timestamp | str | ISO 8601 timestamp |
| file_path | str | Approved file path |
| risk_acknowledgement | bool | Must be True |

## Snapshot Lifecycle

1. **Capture** — snapshot created from current governance state
2. **Store** — snapshot persisted with unique snapshot_id
3. **Compare** — two snapshots compared via diff system (T1683)
4. **Archive** — old snapshots retained for audit trail

## Constraints

- Snapshots are immutable once captured
- No snapshot may be modified or deleted
- Snapshot storage is local filesystem only (no external services)

## Acceptance Command

```bash
python3 -m pytest tests/unit/test_t1681_t1800_compatibility.py -v --tb=short
```

## Risk Level

Low — documentation and specification only.

## Dependencies

- T1681 (frozen backlog report validator)
- T1521-T1600 (frozen backlog review report CLI)
