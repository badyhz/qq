# Dirty Workspace LOW Risk Policy

## Purpose

Define rules for files classified as LOW risk. These files have no safety impact and are eligible for streamlined handling.

## Rules

### Eligible for Batch Commit

LOW-risk files may be committed in batches. Multiple LOW-risk files may be included in a single commit, provided:
- All files in the batch are LOW risk
- No HIGH or MEDIUM files are mixed in
- The commit message accurately describes the batch

### No Safety Impact

LOW-risk files must have:
- No trading logic
- No execution pathways
- No secret material
- No runtime orchestration

### Test / Doc Only

LOW-risk files are limited to:
- **C (Docs/Readiness):** Documentation, readiness assessments, closeout reports
- **D (Tests):** Test files, test fixtures, test utilities
- **F (Safe/Unrelated):** Config templates, requirements files, non-sensitive utilities

## Review Expectation

LOW-risk files still require a basic review before commit, but the review is lighter:
- Confirm classification is correct
- Confirm no accidental inclusion of non-LOW files
- Confirm content matches stated purpose
