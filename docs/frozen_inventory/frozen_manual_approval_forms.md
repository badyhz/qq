# Frozen Manual Approval Forms

## What This Stage Does

Generates manual approval form templates for each frozen file. Forms contain placeholder fields for human reviewer, decision, signature, and mandatory confirmations.

## What This Stage Does NOT Do

- Does NOT grant any approval
- Does NOT perform any backup/archive/delete
- Does NOT modify frozen files
- Does NOT execute or import frozen files

## Form Types

- `KEEP_FROZEN_REVIEW_FORM` — for files to remain frozen
- `ARCHIVE_AFTER_BACKUP_APPROVAL_FORM` — for archive candidates
- `DELETE_AFTER_BACKUP_APPROVAL_FORM` — for delete candidates
- `OFFLINE_REWRITE_APPROVAL_FORM` — for rewrite candidates
- `NEEDS_MORE_REVIEW_FORM` — for files needing further review

## How to Generate

```bash
PYTHONPATH=. python3 scripts/build_frozen_manual_approval_forms.py \
  --backup-evidence-checklist-dir /tmp/frozen_backup_evidence_checklist \
  --output-dir /tmp/frozen_manual_approval_forms \
  --strict \
  --release-hold HOLD
```

## Outputs

- `/tmp/frozen_manual_approval_forms/manual_approval_forms.json`
- `/tmp/frozen_manual_approval_forms/manual_approval_forms.md`
- `/tmp/frozen_manual_approval_forms/manual_approval_forms_manifest.json`

## Mandatory Confirmations

Every form requires the reviewer to confirm:
1. This is offline-only
2. No file has been executed
3. No file has been imported
4. No file has been copied by automation
5. No file has been moved by automation
6. No file has been deleted by automation
7. release_hold remains HOLD
8. live/testnet/runtime remains disabled
9. backup/archive/delete still requires separate explicit human approval

## Forbidden Confirmations

These may NOT be included as mandatory:
- approve_live_activation
- approve_testnet_activation
- approve_runtime_activation
- approve_immediate_delete
- approve_immediate_move
- approve_automated_backup
- approve_automated_archive

## How to Complete a Form

1. Fill in `reviewer_name` (your name)
2. Fill in `reviewer_role` (your role)
3. Fill in `review_date` (today's date)
4. Review all required evidence
5. Set `human_decision` to one of:
   - `KEEP_FROZEN`
   - `APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP`
   - `APPROVE_PREPARE_DELETE_AFTER_BACKUP`
   - `APPROVE_PREPARE_OFFLINE_REWRITE`
   - `REQUEST_MORE_REVIEW`
   - `REJECT`
6. Fill in `decision_reason`
7. Sign in `signature_placeholder`
8. Confirm all mandatory confirmations

## release_hold HOLD

All forms have `release_hold=HOLD`. No action may proceed until explicitly released.
