# Frozen Approval Outcome Matrix

## What This Does

Builds an outcome matrix from dry-run validation results.
Groups forms by outcome, counts them, and lists forbidden next actions.

## What This Does NOT Do

- No actual approval
- No file operations
- No network access
- No action dispatch

## Matrix Fields

- outcome — The validation outcome
- count — Number of forms with this outcome
- affected_paths — File paths affected
- example_form_ids — Example form IDs
- allowed_next_manual_step — What a human may do next
- forbidden_next_actions — 13 forbidden actions
- requires_more_evidence — Whether more evidence is needed
- requires_human_review — Whether human review is needed
- action_authorized — Always false
- no_action_performed — Always true
- release_hold — Must be HOLD

## Forbidden Next Actions

DELETE_NOW, MOVE_NOW, COPY_NOW, ARCHIVE_NOW, EXECUTE_NOW, IMPORT_NOW,
ACTIVATE_LIVE, ACTIVATE_TESTNET, ENABLE_RUNTIME, ENABLE_PLANNER,
SUBMIT_ORDER, CANCEL_ORDER, FLATTEN_POSITION

## How to Run

```bash
PYTHONPATH=. python3 scripts/build_frozen_approval_outcome_matrix.py \
    --dry-run-validation-dir /tmp/frozen_approval_dry_run_validation \
    --output-dir /tmp/frozen_approval_outcome_matrix \
    --strict \
    --release-hold HOLD
```
