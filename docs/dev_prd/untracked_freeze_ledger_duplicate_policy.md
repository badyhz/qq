# T1169 - Untracked Freeze Ledger: Duplicate Policy

## Detection

- Compute SHA-256 content hash for every untracked file during ledger scan.
- Compare against:
  - All tracked files in the repository.
  - All other untracked files in the current scan.
- If hash matches, mark the file with state=DUPLICATE.

## Canonical Designation

- When duplicates are detected, one file must be designated canonical.
- Canonical selection rules:
  1. Tracked file is always canonical over untracked file.
  2. Among untracked files, the file with more references is canonical.
  3. Among equally referenced files, the file in the standard directory structure is canonical.
  4. If still tied, operator must decide.

## Actions

### Flag
- Mark duplicate file with state=DUPLICATE in ledger.
- Record `canonical_path`, `duplicate_path`, and `content_hash`.

### Recommend Canonical
- Generate recommendation based on canonical selection rules.
- Present recommendation to operator with rationale.

### Human Decision
- Operator decides for each duplicate:
  - KEEP_DUPLICATE: Promote to tracked, remove canonical (requires approval).
  - KEEP_CANONICAL: Delete duplicate (requires approval).
  - KEEP_BOTH: Accept duplication, record reason (requires approval).
  - DEFER: No action, re-review later.

## Evidence Requirements

- Detection is automated (hash comparison); no human approval needed for detection.
- Any action on a duplicate (delete, promote, modify) requires human approval.
- All decisions recorded in ledger as immutable entries.

## Notification

- Immediate notification when duplicate is detected.
- Summary of all duplicates included in periodic ledger reports.
