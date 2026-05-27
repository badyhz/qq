# Dirty Workspace Tracked File Policy

## Purpose

Define rules for files that are tracked by git but have uncommitted modifications.

## Rules

### 1. Do Not Auto-Commit

Tracked modified files must never be auto-committed. Each file requires explicit review.

### 2. Diff Review Required

Before any commit, the diff of each tracked modified file must be reviewed. The review must confirm:
- No secrets or credentials introduced
- No frozen-boundary violations
- No unintended scope changes

### 3. Category-Based Decision

After classification, apply the decision rule for the file's category:

| Category | Decision |
|----------|----------|
| A (Route) | Review diff, commit after approval |
| B (Runtime/Live) | HUMAN_REVIEW_ONLY, freeze |
| C (Docs/Readiness) | Review diff, eligible for batch commit |
| D (Tests) | Review diff, eligible for batch commit |
| E (Scripts) | Review diff, commit after approval |
| F (Safe/Unrelated) | Review diff, eligible for batch commit |
| G (Human Decision) | Escalate to human, no auto-action |
