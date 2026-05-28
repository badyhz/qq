# Frozen File Operator Decision Guide

## Purpose

Guide for operators reviewing frozen files. Use this alongside the human review queue, decision prep, and disposition report.

## Step 1: Review Priority Order

Always review in this order:
1. **P0_CRITICAL_REVIEW** — contains submit/cancel/flatten/live/runtime/binance/fapi
2. **P1_HIGH_REVIEW** — contains testnet/order/exchange
3. **P2_STANDARD_REVIEW** — contains shadow/observation/verify
4. **P3_LOW_REVIEW** — other files
5. **UNKNOWN_REVIEW** — needs classification

## Step 2: Required Evidence Before Any Action

For each file, before making any decision:
- [ ] SHA-256 hash snapshot recorded
- [ ] Full file content backed up (P0/P1)
- [ ] Owner review signoff obtained (P0/P1)
- [ ] Backup integrity verified
- [ ] Diff review completed (archive/delete/rewrite candidates)

## Step 3: Required Questions

For each file, answer:
1. Is this file still needed for any purpose?
2. Does it contain secrets or credentials?
3. Has it been reviewed for live/testnet safety? (P0/P1)
4. Is backup verified before any action? (P0/P1)

## Step 4: Choose Decision

| Decision | When to Use |
|----------|-------------|
| KEEP_FROZEN | Default. No action needed now. |
| ARCHIVE_AFTER_BACKUP | File no longer needed, backup verified. |
| REWRITE_OFFLINE_ONLY | File useful but needs offline-only rewrite. |
| DELETE_AFTER_BACKUP | File harmful/obsolete, backup verified. |
| NEEDS_MORE_REVIEW | Cannot decide yet. |

## Step 5: Record Decision

Replace `final_manual_decision_placeholder` with your decision and your name/date.

## What NOT to Do

- **NEVER** execute a frozen file
- **NEVER** import a frozen file
- **NEVER** activate live/testnet/runtime
- **NEVER** place/cancel/flatten orders
- **NEVER** approve without backup
- **NEVER** skip required evidence
- **NEVER** auto-promote any file

## Safety Reminders

- release_hold = **HOLD**
- advisory_only = **true**
- human_review_required = **true**
- No activation permitted until explicit approval and release_hold change.
