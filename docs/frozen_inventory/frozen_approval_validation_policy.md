# Frozen Approval Validation Policy

## What This Stage Does

Validates generated form templates and optionally completed forms. Ensures all safety invariants hold: no immediate actions approved, release_hold=HOLD, all decisions are placeholders or allowed values.

## What This Stage Does NOT Do

- Does NOT grant any approval
- Does NOT perform any backup/archive/delete
- Does NOT modify forms or frozen files

## How to Validate

```bash
PYTHONPATH=. python3 scripts/validate_frozen_manual_approval_forms.py \
  --manual-approval-forms-dir /tmp/frozen_manual_approval_forms \
  --backup-evidence-checklist-dir /tmp/frozen_backup_evidence_checklist \
  --output-dir /tmp/frozen_approval_validation \
  --strict \
  --release-hold HOLD
```

## Outputs

- `/tmp/frozen_approval_validation/approval_validation.json`
- `/tmp/frozen_approval_validation/approval_validation.md`
- `/tmp/frozen_approval_validation/approval_validation_manifest.json`

## Template Validation Rules

For generated templates, PASS requires:
- All required fields exist
- All decisions are placeholders
- release_hold=HOLD
- advisory_only=true
- No immediate action approved
- Forbidden confirmations listed as forbidden only

## Completed Form Validation Rules

For completed forms, additional rules:
- Missing reviewer_name fails
- Missing decision fails
- Forbidden decision fails
- Cannot approve immediate action
- Cannot override release_hold

## Allowed Human Decisions

- `KEEP_FROZEN`
- `APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP`
- `APPROVE_PREPARE_DELETE_AFTER_BACKUP`
- `APPROVE_PREPARE_OFFLINE_REWRITE`
- `REQUEST_MORE_REVIEW`
- `REJECT`

## Forbidden Decisions

- `DELETE_NOW`, `MOVE_NOW`, `COPY_NOW`, `ARCHIVE_NOW`
- `EXECUTE_NOW`, `IMPORT_NOW`
- `ACTIVATE_LIVE`, `ACTIVATE_TESTNET`
- `ENABLE_RUNTIME`, `ENABLE_PLANNER`

## Important

Even if a human approves `APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP`, automation must NOT perform the actual archive. The approval only means the human has reviewed the evidence and agrees the file is a candidate for future archive. The actual archive requires a separate explicit step.
