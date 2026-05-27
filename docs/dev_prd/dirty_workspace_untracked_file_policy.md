# Dirty Workspace Untracked File Policy

## Purpose

Define rules for files that are not tracked by git (new files not yet added).

## Rules

### 1. Classify Before Commit

Every untracked file must be classified (A-G) before any commit action. No file may be committed without classification.

### 2. HIGH-Risk Files Frozen

Untracked files classified as HIGH risk are frozen immediately:
- No auto-commit
- No auto-wire (no import statements added automatically)
- No auto-run
- Marked as HUMAN_REVIEW_ONLY

### 3. LOW-Risk Files Eligible for Batch Commit

Untracked files classified as LOW risk (categories C, D, F) may be committed in batch after:
- Classification confirmed
- Content review completed
- No frozen-boundary violations detected

### 4. MEDIUM-Risk Files Require Approval

Untracked files classified as MEDIUM risk (categories A, E) require individual human approval before commit.

### 5. CRITICAL Files Blocked

Any file classified as CRITICAL is blocked from all commit actions until explicit human override.
