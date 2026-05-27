# Frozen Backlog Review Audit Orchestrator CLI (T1684)

## Purpose

CLI interface for orchestrating frozen backlog review audits: capturing snapshots, running validators, computing diffs, and generating audit reports.

## Scope

- Pure documentation and specification only
- No runtime execution, no exchange connectors, no secret management
- Release hold: HOLD

## CLI Commands

### `audit snapshot`

Capture a point-in-time snapshot of frozen backlog review state.

```
audit snapshot [--output PATH]
```

- Reads current governance state
- Produces immutable snapshot (T1682)
- Output defaults to `logs/audit/snapshot_{timestamp}.json`

### `audit validate`

Run validator (T1681) against current state or a snapshot.

```
audit validate [--snapshot PATH]
```

- If `--snapshot` provided, validates that snapshot
- Otherwise validates current live governance state
- Outputs validation result (is_valid, errors, warnings)

### `audit diff`

Compare two snapshots.

```
audit diff --a SNAPSHOT_A --b SNAPSHOT_B [--output PATH]
```

- Computes diff (T1683) between two snapshots
- Output defaults to stdout
- JSON or markdown format

### `audit report`

Generate full audit report.

```
audit report [--snapshot PATH] [--format json|md]
```

- Combines validation + snapshot into single report
- Includes compliance status, approval evidence summary, risk inventory

## CLI Constraints

- All commands are read-only
- No write operations to governance state
- No network calls
- No credential access
- Output to local filesystem or stdout only

## Acceptance Command

```bash
python3 -m pytest tests/unit/test_t1681_t1800_compatibility.py -v --tb=short
```

## Risk Level

Low — documentation and specification only. CLI is read-only.

## Dependencies

- T1681 (frozen backlog report validator)
- T1682 (frozen backlog report snapshot)
- T1683 (frozen backlog report diff)
- T1561 (frozen backlog review report CLI usage doc)
