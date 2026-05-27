# T1088 - Freeze-Aware Task PARTIAL State

## Purpose

Define the lifecycle of the PARTIAL state.

## Entry Conditions

A task enters PARTIAL when:

1. An agent completes some but not all acceptance criteria.
2. A human requests modifications, leaving existing work intact.
3. A runtime interruption prevents full completion.

## Exit Conditions

A task exits PARTIAL when:

1. The remaining acceptance criteria are met -> transitions to COMPLETED.
2. A human determines the task should be abandoned -> transitions to DENIED.
3. A dependency change makes the remaining work impossible -> transitions
   to BLOCKED.

## Completion Criteria

To move from PARTIAL to COMPLETED:

1. ALL acceptance criteria must be satisfied.
2. No frozen file violations must exist.
3. The task must pass the verification command (if defined).

## Partial Progress Preservation

- Completed sub-criteria are tracked individually.
- On re-entry to IN_PROGRESS, the agent sees which criteria are met.
- No completed work is discarded unless explicitly reset by a human.

## Safety Statement

PARTIAL preserves progress. It does not imply failure; it indicates
incomplete success.
