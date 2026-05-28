# Frozen Completed Form Simulation

## What This Does

Generates simulated completed approval forms from manual approval form templates.
Each simulated form represents what a completed form would look like if a human reviewer
filled it in with a specific decision and evidence status.

## What This Does NOT Do

- No actual approval granted
- No file operations performed
- No network access
- No exchange interaction
- No backup/archive/delete/move/copy/rename
- No action dispatch

## Simulation Categories (25)

1. `valid_keep_frozen` — Valid form with KEEP_FROZEN decision
2. `valid_prepare_archive_after_backup` — Valid form with archive preparation
3. `valid_prepare_delete_after_backup` — Valid form with delete preparation
4. `valid_prepare_offline_rewrite` — Valid form with rewrite preparation
5. `request_more_review` — Form requesting additional review
6. `reject` — Form with REJECT decision
7. `missing_reviewer` — Form with empty reviewer name
8. `missing_decision` — Form with empty decision
9-18. `forbidden_*` — Forms with forbidden immediate actions (DELETE_NOW, MOVE_NOW, etc.)
19. `release_hold_override` — Form attempting to override release_hold
20. `missing_evidence_for_archive` — Archive request without evidence
21. `missing_evidence_for_delete` — Delete request without evidence
22. `incomplete_hash_evidence` — Missing hash verification
23. `incomplete_rollback_evidence` — Missing rollback verification
24. `conflicting_confirmations` — Forbidden confirmations checked as mandatory
25. `unsafe_auto_action_requested` — Automated action flag set

## How to Run

```bash
PYTHONPATH=. python3 scripts/build_frozen_completed_form_simulations.py \
    --manual-approval-forms-dir /tmp/frozen_manual_approval_forms \
    --backup-evidence-checklist-dir /tmp/frozen_backup_evidence_checklist \
    --output-dir /tmp/frozen_completed_form_simulations \
    --strict \
    --release-hold HOLD
```

## Outputs

- `completed_form_simulations.json` — All simulated forms
- `completed_form_simulations.md` — Markdown report
- `completed_form_simulations_manifest.json` — Manifest with hash

## Safety

- release_hold must be HOLD
- All forms are dry_run_only=true
- No action_requested except unsafe fixture
- No action performed
- Deterministic output
