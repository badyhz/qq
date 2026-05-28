# Frozen File Disposition Report

## What This Stage Does

Renders a comprehensive human-friendly disposition report combining the human review queue and archive/delete decision prep. Includes all 18 sections: executive summary, safety boundary, priority/disposition breakdowns, P0/P1 items, archive/delete/rewrite candidates, required decisions, forbidden actions, and next safe actions.

## What It Does NOT Do

- Does NOT recommend any activation
- Does NOT approve any action
- Does NOT perform any file operations
- Does NOT modify frozen files

## How to Render Report

```bash
PYTHONPATH=. python3 scripts/render_frozen_file_disposition_report.py \
  --human-review-queue-dir /tmp/frozen_human_review_queue \
  --decision-prep-dir /tmp/frozen_archive_delete_decision_prep \
  --output-dir /tmp/frozen_file_disposition_report \
  --strict --release-hold HOLD
```

## Output Files

- frozen_file_disposition_report.json — machine-readable
- frozen_file_disposition_report.md — human-readable markdown
- frozen_file_disposition_report.html — standalone offline HTML
- frozen_file_disposition_manifest.json — summary manifest

## Report Sections

1. Executive Summary
2. Safety Boundary
3. Frozen File Count
4. Priority Breakdown
5. Disposition Breakdown
6. P0 Critical Review Items
7. P1 High Review Items
8. Archive Candidates
9. Delete After Backup Candidates
10. Offline Rewrite Candidates
11. Keep Frozen Items
12. Unknown Items
13. Required Human Decisions
14. Required Backup Evidence
15. Forbidden Actions
16. No-Touch Statement
17. release_hold HOLD Statement
18. Next Safe Actions

## HTML Report

- Standalone offline HTML
- No CDN, no external JS, no web server required
- Open directly in any browser

## Safety

- release_hold: **HOLD**
- advisory_only: **true**
- human_review_required: **true**
- No activation permitted.
