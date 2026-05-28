# Frozen Approval Dry-Run Validator

## What This Does

Validates simulated completed forms in dry-run mode.
Classifies each form into one of 10 outcomes.

## What This Does NOT Do

- No actual approval granted
- No file operations
- No network access
- No action dispatch

## Outcomes

- `DRY_RUN_ACCEPTED_PREPARE_ONLY` — Form passed validation, prepare-only
- `DRY_RUN_REJECTED_FORBIDDEN_DECISION` — Forbidden decision detected
- `DRY_RUN_REJECTED_MISSING_REVIEWER` — Reviewer name empty
- `DRY_RUN_REJECTED_MISSING_DECISION` — Decision empty
- `DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE` — release_hold not HOLD
- `DRY_RUN_REJECTED_MISSING_EVIDENCE` — Evidence incomplete
- `DRY_RUN_REJECTED_CONFLICTING_CONFIRMATIONS` — Conflicting confirmations
- `DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST` — Auto action requested
- `DRY_RUN_NEEDS_MORE_REVIEW` — Additional review needed
- `DRY_RUN_REJECTED` — Other rejection reason

## How Accepted Prepare-Only Differs from Action Authorization

"Accepted prepare-only" means the form passed all validation checks.
It does NOT authorize any action. No backup, archive, delete, move, copy,
rename, or activation is performed or authorized.

## How to Run

```bash
PYTHONPATH=. python3 scripts/run_frozen_approval_dry_run_validator.py \
    --completed-form-simulations-dir /tmp/frozen_completed_form_simulations \
    --output-dir /tmp/frozen_approval_dry_run_validation \
    --strict \
    --release-hold HOLD
```

## Safety

- release_hold must be HOLD
- action_authorized is always False
- No action performed
