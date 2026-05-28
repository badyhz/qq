# Frozen Rollback Plan

## Overview

The rollback plan documents how to restore frozen files if a future archive/delete/rewrite action needs to be reversed. All restore commands are documentation templates only — no automated restore is possible.

## Safety Boundary

- `forbidden_automated_restore`: **true** for all items
- `human_approval_required`: **true** for all items
- `no_execution`: **true** for all items
- `no_import`: **true** for all items
- `release_hold`: **HOLD**

## Rollback Preconditions

Every rollback requires:
1. Backup manifest hash verified
2. Human approval obtained
3. Release hold lifted
4. Backup integrity confirmed

## Verification Steps

1. Verify backup manifest hash
2. Verify backup file hash
3. Verify restored file hash
4. Human confirmation required

## Manual Restore Command Templates

Each item includes a manual restore command template. These are documentation only:
- They describe the steps a human would take
- They are NOT executable by any script in this system
- No script performs rollback operations

## No Automated Restore

This module explicitly forbids automated restore. All rollback operations require:
- Human operator intervention
- Hash verification
- Human approval
