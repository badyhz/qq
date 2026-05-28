# Frozen Inventory Archive Plan

## Purpose

Design a future no-touch archive/migration plan without performing any actual file operations.

## Key Principle

This plan is advisory only. It proposes future actions but never:
- Moves files
- Deletes files
- Renames files
- Modifies files
- Stages files

## Path Categories

| Category | Description |
|----------|-------------|
| keep_frozen | No action needed |
| human_review_queue | Awaiting human decision |
| archive_candidates | Can be archived after approval |
| rewrite_candidates | Must be rewritten after approval |
| delete_after_backup_candidates | Can be deleted after backup verification |
| unknown_review_required | Full inspection needed |

## Proposed Actions

| Disposition | Proposed Action |
|-------------|----------------|
| KEEP_FROZEN | NO_ACTION |
| NEEDS_HUMAN_REVIEW | AWAIT_HUMAN_DECISION |
| CANDIDATE_FOR_ARCHIVE | MOVE_TO_ARCHIVE_AFTER_APPROVAL |
| CANDIDATE_FOR_REWRITE | REWRITE_FROM_SCRATCH_AFTER_APPROVAL |
| CANDIDATE_FOR_DELETION_AFTER_BACKUP | BACKUP_THEN_DELETE_AFTER_APPROVAL |
| UNKNOWN | AWAIT_HUMAN_DECISION |

## Safety Boundary

- No actual file moves
- No actual file deletes
- No actual file renames
- No actual file modifications
- Plan-only. No-touch confirmed.
- release_hold = HOLD
- Advisory only. Human review required.

## CLI

```bash
python3 scripts/build_frozen_inventory_archive_plan.py \
    --decision-matrix-dir /tmp/frozen_inventory_decision_matrix \
    --output-dir /tmp/frozen_inventory_archive_plan \
    --strict \
    --release-hold HOLD
```

## Outputs

- `archive_plan.json` — full plan
- `archive_plan.md` — human-readable summary
- `archive_plan_manifest.json` — manifest with safety flags
