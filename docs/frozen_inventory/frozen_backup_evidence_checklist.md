# Frozen Backup Evidence Checklist

## What This Stage Does

Generates per-file evidence checklist items that a human must complete before any future backup/archive/delete action. Each item specifies exactly what evidence (hash, size, path, owner, rollback plan) must be collected.

## What This Stage Does NOT Do

- Does NOT perform any backup
- Does NOT perform any archive/delete/move/copy
- Does NOT execute or import frozen files
- Does NOT grant any approval
- Does NOT modify frozen files

## How to Generate

```bash
PYTHONPATH=. python3 scripts/build_frozen_backup_evidence_checklist.py \
  --backup-manifest-dir /tmp/frozen_backup_manifest \
  --archive-simulation-dir /tmp/frozen_archive_simulation \
  --output-dir /tmp/frozen_backup_evidence_checklist \
  --strict \
  --release-hold HOLD
```

## Outputs

- `/tmp/frozen_backup_evidence_checklist/backup_evidence_checklist.json`
- `/tmp/frozen_backup_evidence_checklist/backup_evidence_checklist.md`
- `/tmp/frozen_backup_evidence_checklist/backup_evidence_checklist_manifest.json`

## How to Interpret Blockers

Each item has a `blocker_status`:
- `BLOCKED_PENDING_EVIDENCE` — hash/size/path evidence not yet collected
- `BLOCKED_PENDING_OWNER` — no human owner assigned
- `BLOCKED_PENDING_HASH_REVIEW` — hash not independently verified
- `BLOCKED_PENDING_ROLLBACK_REVIEW` — rollback plan not reviewed
- `BLOCKED_PENDING_HUMAN_APPROVAL` — awaiting human decision
- `REVIEW_REQUIRED` — needs more review before any action

No item may be `COMPLETE`, `BACKUP_DONE`, `APPROVED`, or `SAFE_TO_DELETE`.

## How to Collect Hash Evidence Manually

1. Open the frozen file (read-only)
2. Compute SHA256: `sha256sum <file>`
3. Record hash in evidence file
4. Cross-check with manifest hash
5. Document any discrepancy

## How to Collect Backup Evidence Manually

1. Verify file exists at original path
2. Record file size
3. Record file permissions/owner
4. Document proposed backup destination (simulation only)
5. Do NOT actually copy the file

## How to Collect Rollback Evidence Manually

1. Identify rollback plan ID from checklist
2. Review rollback plan contents
3. Confirm rollback path is valid
4. Document rollback feasibility

## release_hold HOLD

All items have `release_hold=HOLD`. No action may proceed until explicitly released by human authority.

## advisory_only true

All items are advisory only. They inform human decision-making but do not trigger any automated action.

## human_review_required true

Every item requires human review before any action.
