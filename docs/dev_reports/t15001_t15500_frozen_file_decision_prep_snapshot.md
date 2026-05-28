# T15001-T15500 Frozen File Decision Prep Snapshot

## Current State

- 25 frozen files in human review queue
- 25 decision prep items generated
- All items: deletion_allowed_now=false, archive_allowed_now=false
- All items: required_human_approval=true, no_touch_until_approved=true

## Priority Breakdown

- P0_CRITICAL_REVIEW: files with submit/cancel/flatten/live/runtime keywords
- P1_HIGH_REVIEW: files with testnet/order/exchange keywords
- P2_STANDARD_REVIEW: files with shadow/observation/verify keywords
- UNKNOWN_REVIEW: files with no risk keywords

## Candidate Actions

- KEEP_FROZEN: default for all items
- PREPARE_ARCHIVE_AFTER_BACKUP: for archive candidates
- PREPARE_OFFLINE_REWRITE: for rewrite candidates
- NEEDS_MORE_REVIEW: for items needing further classification

## Safety Boundary

- No immediate deletion/archive/rewrite permitted
- All actions require human approval
- All actions require backup verification
- release_hold remains HOLD

## Regeneration

```bash
PYTHONPATH=. python3 scripts/build_frozen_human_review_queue.py \
  --decision-matrix-dir /tmp/frozen_inventory_decision_matrix \
  --output-dir /tmp/frozen_human_review_queue \
  --strict --release-hold HOLD

PYTHONPATH=. python3 scripts/build_frozen_archive_delete_decision_prep.py \
  --human-review-queue-dir /tmp/frozen_human_review_queue \
  --output-dir /tmp/frozen_archive_delete_decision_prep \
  --strict --release-hold HOLD
```
