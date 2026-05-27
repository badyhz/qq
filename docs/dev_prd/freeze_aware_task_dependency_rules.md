# T1084 - Freeze-Aware Task Dependency Rules

## Purpose

Define dependency types and validation rules for the task queue.

## Dependency Types

| Type | Meaning |
|---|---|
| BLOCKS | This task prevents the target from starting |
| BLOCKED_BY | This task cannot start until the target completes |
| REQUIRES | This task needs the target's output as input |
| ENABLES | This task, on completion, makes the target eligible |

## Normalization

All four types are bidirectional mirrors:

- `A BLOCKS B` is equivalent to `B BLOCKED_BY A`.
- `A ENABLES B` is equivalent to `B REQUIRES A`.

The queue stores edges in one canonical direction and derives the inverse.

## Validation Rules

### No Cycles

After building the dependency graph, perform a topological sort. If the
sort fails, a cycle exists. The result includes `cycle_detected=True` and
the offending task IDs in `missing_deps`.

### No Orphan Dependencies

Every task referenced by a dependency edge MUST exist in the queue. If a
referenced task is missing, it is reported in `orphans`.

### Self-Dependency Prohibited

A task MUST NOT depend on itself. This is rejected at registration time.

## Dependency Result Structure

```
DependencyResult(
    valid=<bool>,
    missing_deps=(<task_ids>),
    cycle_detected=<bool>,
    orphans=(<task_ids>),
)
```

## Safety Statement

Dependency validation is a pure graph operation. No side effects.
