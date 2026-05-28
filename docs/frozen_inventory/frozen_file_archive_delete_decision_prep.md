# Frozen File Archive/Delete Decision Prep

## What This Stage Does

Prepares archive/delete decision data for each frozen file. For every file in the human review queue, produces candidate action, backup requirements, rollback plan, and safety flags.

## What It Does NOT Do

- Does NOT actually archive, delete, or move any file
- Does NOT execute any file operations
- Does NOT approve any action
- Does NOT bypass human review

## How to Regenerate Decision Prep

```bash
PYTHONPATH=. python3 scripts/build_frozen_archive_delete_decision_prep.py \
  --human-review-queue-dir /tmp/frozen_human_review_queue \
  --output-dir /tmp/frozen_archive_delete_decision_prep \
  --strict --release-hold HOLD
```

## Candidate Actions

| Action | Description |
|--------|-------------|
| KEEP_FROZEN | No action planned, file remains frozen |
| PREPARE_ARCHIVE_AFTER_BACKUP | Prepare for archive, requires backup first |
| PREPARE_DELETE_AFTER_BACKUP | Prepare for deletion, requires backup first |
| PREPARE_OFFLINE_REWRITE | Prepare for offline-only rewrite |
| NEEDS_MORE_REVIEW | More human review needed |

## Safety Boundary

- deletion_allowed_now: **false** (all items)
- archive_allowed_now: **false** (all items)
- rewrite_allowed_now: **false** (all items)
- required_human_approval: **true** (all items)
- no_touch_until_approved: **true** (all items)

## Forbidden Immediate Actions

DELETE_NOW, MOVE_NOW, EXECUTE_NOW, IMPORT_NOW, ACTIVATE_NOW

## How to Prepare Backup Evidence

1. Generate SHA-256 hash of each file
2. Create full file content backup to secure location
3. Record backup location
4. Verify backup integrity
5. Obtain owner signoff for P0/P1 items

## How to Record Human Decision

Replace `final_manual_decision_placeholder` value with the approved decision after human review.

## No-Touch Statement

release_hold: **HOLD**. No activation permitted. All files remain untouched until explicit human approval.
