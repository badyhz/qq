# Dirty Workspace HIGH Risk Policy

## Purpose

Define strict rules for files classified as HIGH risk. These files pose the greatest safety concern and require maximum caution.

## Rules

### HUMAN_REVIEW_ONLY

HIGH-risk files are subject to HUMAN_REVIEW_ONLY enforcement:
- No automated tool may commit these files
- No automated tool may modify these files
- No automated tool may execute these files
- A human must explicitly review and approve every action

### No Auto-Commit

HIGH-risk files must never appear in an automated commit. Even if staged manually, the commit must be initiated by a human.

### No Auto-Wire

HIGH-risk files must not have their imports, references, or dependencies automatically wired into other modules. Any integration must be human-directed.

### No Auto-Run

HIGH-risk files must not be executed by automated pipelines, scripts, or CI systems without explicit human configuration.

## Freeze Inventory

HIGH-risk files are tracked in the freeze inventory. See `dirty_workspace_high_risk_freeze_inventory.md` for the current list of frozen files and their status.

## Rationale

HIGH-risk files typically contain:
- Live trading execution logic
- Exchange API interaction
- Order submission pathways
- Runtime orchestration with real-money exposure

Accidental commit or execution of these files could result in unintended live trading activity.
