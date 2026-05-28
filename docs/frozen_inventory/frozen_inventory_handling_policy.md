# Frozen Inventory Handling Policy

**release_hold = HOLD**
**advisory_only = True**
**human_review_required = True**

## Hard Rules

### What Agents MUST NOT Do

1. **No execution**: Never run any frozen file as a script or module.
2. **No import**: Never import any frozen file into Python code.
3. **No staging**: Never `git add` any frozen file.
4. **No modification**: Never edit, rename, or delete any frozen file.
5. **No network**: Never allow any frozen file to connect to Binance or any network.
6. **No order placement**: Never allow any frozen file to place, cancel, or flatten orders.
7. **No auto-promotion**: Never promote frozen files to active status without explicit human approval.
8. **No `git add .`**: Always use explicit file paths when staging.

### What Agents MAY Do

1. **Read metadata**: Use `git status --short`, `ls -lh`, `wc -l`, `head -40` for inventory.
2. **Read small text**: Use Python `pathlib.read_text()` for files under 512KB.
3. **Compute hashes**: Use `hashlib.sha256` for integrity verification.
4. **Generate reports**: Create inventory documentation in `docs/frozen_inventory/`.
5. **Run scanner**: Execute `core/frozen_inventory_audit.py` and `scripts/build_frozen_inventory_report.py`.
6. **Run tests**: Execute `tests/unit/test_frozen_inventory_audit.py`.

## Release Hold Policy

- `release_hold` must remain `HOLD` until explicit human authorization.
- Any change to `release_hold` status requires:
  1. Human review of all frozen files
  2. Explicit written approval
  3. Updated documentation
  4. New inventory scan after changes

## Disposition Categories

Each frozen file should be assigned one of:

| Disposition | Description |
|-------------|-------------|
| KEEP_FROZEN | File remains frozen, no action needed |
| NEEDS_HUMAN_REVIEW | File requires human inspection before any action |
| CANDIDATE_FOR_ARCHIVE | File may be archived (moved to archive directory) |
| CANDIDATE_FOR_REWRITE | File needs rewrite with safety constraints |
| CANDIDATE_FOR_DELETION_AFTER_BACKUP | File may be deleted after backup |
| UNKNOWN | Disposition not yet determined |

## File Status Tracking

| Status | Description |
|--------|-------------|
| untracked | File exists but is not tracked by git |
| tracked | File is tracked by git |
| modified | File has uncommitted modifications |
| missing | File expected but not found |
