# T1082 - Freeze-Aware Task Admission Rules

## Purpose

Define the criteria a task must satisfy before the queue admits it for
execution.

## Admission Criteria

### 1. No Frozen File Overlap

For every file `f` in the task's explicit file list:

- `f` MUST NOT appear in the frozen file set.

If any file overlaps, the task is denied with reason category
`FREEZE_CONFLICT`.

### 2. No HIGH-Risk File Touch

For every file `f` in the task's explicit file list:

- `f` MUST NOT be tagged as HIGH-risk in the risk registry.

If any file is HIGH-risk, the task is denied with reason category
`HIGH_RISK_TOUCH`.

### 3. Dependencies Met

For every dependency `d` declared by the task:

- `d` MUST be in state COMPLETED or PASS.

If any dependency is missing or incomplete, the task is denied with reason
category `MISSING_DEP`.

### 4. Risk Level Acceptable

The task's declared risk level MUST be within the configured threshold.

If the risk level exceeds the threshold, the task is denied with reason
category `SAFETY_VIOLATION`.

## Admission Result

On success: `AdmittedResult(admitted=True, task_id=..., reason="ok")`

On failure: `AdmittedResult(admitted=False, task_id=..., reason=<category>,
blocking_freeze_files=(...))`

## Safety Statement

Admission is a pure read-only decision. No side effects.
