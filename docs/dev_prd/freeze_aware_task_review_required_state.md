# T1086 - Freeze-Aware Task HUMAN_REVIEW_REQUIRED State

## Purpose

Define the lifecycle of the HUMAN_REVIEW_REQUIRED state.

## Entry Conditions

A task enters HUMAN_REVIEW_REQUIRED when:

1. The task touches a file that requires human sign-off (per policy).
2. An agent explicitly requests human review after partial completion.
3. A risk check flags the task for manual inspection.

## Exit Conditions

A task exits HUMAN_REVIEW_REQUIRED when:

1. A human approves the task -> transitions to IN_PROGRESS or PASS.
2. A human rejects the task -> transitions to DENIED.
3. A human requests modifications -> transitions to PARTIAL.

## Escalation Rules

- If no human action is taken within the configured timeout, the task
  remains in HUMAN_REVIEW_REQUIRED.
- The queue emits a reminder event at each escalation interval.
- After max escalation attempts, the task is flagged for administrative
  review.

## Timeout Handling

- Default timeout: configurable per queue.
- On timeout: task stays in HUMAN_REVIEW_REQUIRED; no automatic state
  change.
- The queue NEVER auto-approves or auto-rejects a task in this state.

## Safety Statement

This state is a hard gate. No agent may bypass it. Only explicit human
action changes the state.
