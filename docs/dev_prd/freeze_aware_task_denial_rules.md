# T1083 - Freeze-Aware Task Denial Rules

## Purpose

Define the reasons a task may be denied admission and the associated
metadata.

## Denial Reasons

### FREEZE_CONFLICT

- **Trigger:** Task file list overlaps frozen file set.
- **Metadata:** `related_freeze_file` set to the conflicting file.
- **Resolution:** Remove conflicting files from task or unfreeze.

### HIGH_RISK_TOUCH

- **Trigger:** Task file list contains a HIGH-risk file.
- **Metadata:** `related_freeze_file` set to the HIGH-risk file.
- **Resolution:** Split task to isolate HIGH-risk files into a
  human-reviewed subtask.

### MISSING_DEP

- **Trigger:** A declared dependency is not in COMPLETED or PASS state.
- **Metadata:** `related_task_id` set to the missing dependency.
- **Resolution:** Wait for dependency to complete or restructure task graph.

### SAFETY_VIOLATION

- **Trigger:** Task risk level exceeds configured threshold.
- **Metadata:** `message` describes the specific violation.
- **Resolution:** Reduce risk level or request human override.

## Denial Result Structure

```
DenialReason(
    reason_id=<unique>,
    category=<one of the four above>,
    message=<human-readable>,
    related_task_id=<optional>,
    related_freeze_file=<optional>,
)
```

## Safety Statement

Denial is deterministic and reversible. A denied task may be resubmitted
after the blocking condition is resolved.
