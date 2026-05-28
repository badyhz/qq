# T15001-T15500 Next Safe Actions

## Immediate Next Actions

1. **Review P0 Critical Items** — Files with submit/cancel/flatten/live/runtime keywords require senior operator review first.

2. **Verify Backup Evidence** — For all archive/delete/rewrite candidates, verify SHA-256 hash and backup integrity before recording any decision.

3. **Record Human Decisions** — Replace `final_manual_decision_placeholder` with approved decision after review.

4. **Classify Unknown Items** — Files in UNKNOWN_REVIEW need category assignment before proceeding.

## What NOT to Do

- Do NOT execute any frozen file
- Do NOT import any frozen file
- Do NOT activate live/testnet/runtime
- Do NOT place/cancel/flatten orders
- Do NOT approve without backup
- Do NOT skip required evidence
- Do NOT auto-promote any file

## Safety Reminders

- release_hold = HOLD
- advisory_only = true
- human_review_required = true
- No activation permitted.

## Recommended Next Phase

**T15501-T16000: Offline Backup Manifest / Archive Simulation**

Purpose: Prepare backup manifests and simulate archive operations without actually moving or deleting files. Still no actual file operations.

## Regeneration Commands

```bash
# Full pipeline
PYTHONPATH=. python3 scripts/build_frozen_human_review_queue.py \
  --decision-matrix-dir /tmp/frozen_inventory_decision_matrix \
  --output-dir /tmp/frozen_human_review_queue \
  --strict --release-hold HOLD

PYTHONPATH=. python3 scripts/build_frozen_archive_delete_decision_prep.py \
  --human-review-queue-dir /tmp/frozen_human_review_queue \
  --output-dir /tmp/frozen_archive_delete_decision_prep \
  --strict --release-hold HOLD

PYTHONPATH=. python3 scripts/render_frozen_file_disposition_report.py \
  --human-review-queue-dir /tmp/frozen_human_review_queue \
  --decision-prep-dir /tmp/frozen_archive_delete_decision_prep \
  --output-dir /tmp/frozen_file_disposition_report \
  --strict --release-hold HOLD
```
