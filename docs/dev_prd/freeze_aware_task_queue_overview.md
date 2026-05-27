# T1081 - Freeze-Aware Task Queue Overview

## Purpose

The freeze-aware task queue coordinates agent task execution while respecting
frozen file boundaries. It prevents agents from modifying frozen files,
enforces admission/denial rules, and tracks task lifecycle states.

## Freeze Integration

- Every task carries an explicit file list.
- Before admission, the queue compares the task file list against the
  frozen file set.
- Any overlap causes automatic denial with a `FREEZE_CONFLICT` reason.
- The queue never modifies the frozen set; it reads it as an immutable input.

## Task States

| State | Meaning |
|---|---|
| NOT_STARTED | Task registered, not yet admitted |
| IN_PROGRESS | Task admitted and running |
| COMPLETED | All acceptance criteria met |
| HUMAN_REVIEW_REQUIRED | Needs human sign-off before proceeding |
| BLOCKED | Cannot proceed due to dependency or freeze |
| PARTIAL | Some criteria met, some remain |
| PASS | Final acceptance; no further work |
| DENIED | Rejected by admission rules |

## Admission Rules

A task is admitted when ALL of the following hold:

1. No file in the task file list appears in the frozen file set.
2. No file in the task file list is tagged HIGH-risk.
3. All declared dependencies are in COMPLETED or PASS state.
4. The task risk level is within the configured threshold.

## Denial Rules

A task is denied when ANY of the following hold:

1. At least one task file overlaps a frozen file.
2. At least one task file is HIGH-risk.
3. A required dependency is not in COMPLETED or PASS state.
4. The task violates a safety boundary.

## Safety Statement

This queue is a coordination layer only. It does not execute tasks, touch
files, or communicate with any external system. All outputs are
deterministic and derived from immutable inputs.
