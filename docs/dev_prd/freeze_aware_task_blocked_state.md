# T1087 - Freeze-Aware Task BLOCKED State

## Purpose

Define the lifecycle of the BLOCKED state.

## Entry Conditions

A task enters BLOCKED when:

1. A dependency is not in COMPLETED or PASS state.
2. The task's file list overlaps the frozen file set.
3. A hold is active on the queue and the task is affected.

## Exit Conditions

A task exits BLOCKED when:

1. All blocking dependencies reach COMPLETED or PASS -> transitions to
   NOT_STARTED (re-evaluated for admission).
2. The frozen file overlap is resolved (files unfrozen) -> transitions to
   NOT_STARTED.
3. The queue hold is released -> transitions to NOT_STARTED.

## Unblock Criteria

All of the following must be true for unblock:

1. No task file overlaps a frozen file.
2. All dependencies are satisfied.
3. No active hold affects this task.

## State Preservation

While BLOCKED:

- The task retains its original file list and dependencies.
- No agent may work on the task.
- The task's partial progress (if any) is preserved.

## Safety Statement

BLOCKED is a waiting state. No work is performed. No state is lost.
