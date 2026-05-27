# Dirty Workspace Duplicate File Policy

## Purpose

Define rules for handling duplicate files in the workspace — files with identical or near-identical content that exist in multiple locations.

## Example

`evidence_recorder.py` exists in both `core/` and `utils/`. This is a duplicate that must be resolved before commit.

## Rules

### 1. Deduplicate Before Commit

No duplicate files may be committed. Every duplicate pair must be resolved before either copy is committed.

### 2. Keep Canonical Location

For each duplicate pair, determine the canonical location based on:
- Module responsibility (core vs. utils)
- Import graph (which location is imported by other modules)
- Project structure conventions

The canonical copy is retained. The non-canonical copy is marked for deletion.

### 3. Delete Duplicate Only with Human Confirmation

The non-canonical duplicate must not be deleted automatically. A human must confirm:
- The canonical copy is correct
- No references to the duplicate exist
- Deletion will not break any imports or tests

### 4. Document Resolution

The resolution of each duplicate pair must be documented:
- Which file is canonical
- Why that location was chosen
- What happened to the duplicate (deleted, moved, archived)
