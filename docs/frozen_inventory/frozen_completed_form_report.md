# Frozen Completed Form Report

## What This Does

Renders a comprehensive report from simulation, validation, and outcome matrix data.
Includes 16 sections covering all aspects of the dry-run validation.

## What This Does NOT Do

- No actual approval
- No file operations
- No network access
- No action dispatch

## Report Sections

1. Executive Summary
2. Safety Boundary
3. Simulation Scope
4. Completed Form Categories
5. Accepted Prepare-Only Outcomes
6. Rejected Forbidden Decisions
7. Rejected Missing Evidence
8. Release Hold Override Attempts
9. Unsafe Auto Action Requests
10. Outcome Matrix
11. Pending Human Review
12. No Action Authorized Statement
13. No File Operation Statement
14. Forbidden Actions
15. release_hold HOLD Statement
16. Next Safe Actions

## How to Run

```bash
PYTHONPATH=. python3 scripts/render_frozen_completed_form_report.py \
    --completed-form-simulations-dir /tmp/frozen_completed_form_simulations \
    --dry-run-validation-dir /tmp/frozen_approval_dry_run_validation \
    --outcome-matrix-dir /tmp/frozen_approval_outcome_matrix \
    --output-dir /tmp/frozen_completed_form_report \
    --strict \
    --release-hold HOLD
```

## HTML Output

Standalone offline HTML. No CDN, no external JS, no web server required.
