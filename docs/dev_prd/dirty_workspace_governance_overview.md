# Dirty Workspace Governance Overview

## Purpose

Define rules for managing a dirty git workspace — uncommitted tracked changes and untracked files — to prevent unsafe commits, frozen file contamination, and risk mixing.

## Scope

Applies to all files in the qq repository workspace that are modified (tracked) or untracked at the time of a governance check. Covers classification, risk assessment, commit isolation, and enforcement.

## Classification Policy

Files are classified into categories A through G based on path, content, and risk profile. See `dirty_workspace_classification_policy.md` for full definitions.

## Risk Levels

| Level    | Action                                |
|----------|---------------------------------------|
| LOW      | Eligible for batch commit after review |
| MEDIUM   | Review required, human approval needed |
| HIGH     | HUMAN_REVIEW_ONLY, frozen             |
| CRITICAL | Blocked, no action without explicit override |

## Enforcement

- No `git add .` or `git add -A`.
- Explicit file list per commit.
- HIGH-risk files never auto-committed, auto-wired, or auto-run.
- Duplicate files must be deduplicated before commit.
- Mixed-risk commits are blocked.

## Safety Statement

This governance layer exists to prevent accidental exposure of live trading logic, runtime secrets, and frozen-boundary violations. Every commit is a deployment decision. Treat dirty workspace state as a safety signal, not an inconvenience.
