# Dirty Workspace Commit Isolation Policy

## Purpose

Define rules for isolating commits by risk level to prevent contamination of safe changes with dangerous ones.

## Rules

### 1. Never Mix HIGH and LOW Risk in Same Commit

A single commit must never contain both HIGH-risk and LOW-risk files. This prevents a routine documentation commit from being blocked by a HIGH-risk review requirement.

### 2. Explicit File List Per Commit

Every commit must specify an explicit file list. No wildcard staging is permitted.

Prohibited:
- `git add .`
- `git add -A`
- `git add directory/` (without file-level review)

Required:
- `git add path/to/specific/file.py`
- Each file in the list must be individually reviewed

### 3. Commit Grouping Rules

| Risk Level | May Group With |
|------------|---------------|
| LOW        | LOW only      |
| MEDIUM     | MEDIUM only   |
| HIGH       | HIGH only (requires explicit human approval) |
| CRITICAL   | CRITICAL only (blocked by default) |

### 4. Commit Message Must Reflect Content

The commit message must accurately describe all files included. If a commit contains files from multiple categories (all same risk level), the message must mention each category.

## Rationale

Commit isolation ensures that:
- A failed HIGH-risk review does not block LOW-risk progress
- Rollback scope is minimized
- Audit trail is clear and per-concern
