# Restore to Tags Recovery

## Symptoms
- Need to restore to a known good state
- Current state is broken or unknown
- Need to verify against tagged releases

## Likely Causes
- Code regression introduced
- Bad commit merged
- Test suite broken at HEAD
- Need to compare against known-good tag

## Available Tags
| Tag | Description |
|-----|-------------|
| `multi-strategy-research-deep-hardening-complete` | Deep hardening complete |
| `multi-strategy-research-artifact-browser-complete` | Artifact browser complete |
| `multi-strategy-research-comparison-analytics-complete` | Comparison analytics complete |
| `multi-strategy-research-human-review-complete` | Human review complete |

## Commands to Inspect
```bash
# List all tags
git tag -l

# Check current HEAD
git log --oneline -1

# Show tag details
git show multi-strategy-research-human-review-complete --stat

# Compare current to tag
git diff multi-strategy-research-human-review-complete..HEAD --stat
```

## Safe Recovery Commands
```bash
# Create a backup branch first
git branch backup-$(date +%Y%m%d-%H%M%S)

# Check out tag (detached HEAD)
git checkout multi-strategy-research-human-review-complete

# Or create a branch from tag
git checkout -b restore-from-tag multi-strategy-research-human-review-complete

# Verify test suite at tag
PYTHONPATH=. .venv/bin/pytest -q

# If satisfied, reset main to tag
# git checkout main
# git reset --hard multi-strategy-research-human-review-complete
```

## Forbidden Recovery Commands
- Do not force-push reset to remote
- Do not delete tags
- Do not modify tag history
- Do not reset without backup branch

## Escalation Rule
If restore to tag is needed:
1. Create backup branch first
2. Verify tag state passes tests
3. If tests fail at tag, tag may be corrupted
4. Escalate if tag state is also broken

## Final Verification
```bash
# Verify at tag state
git log --oneline -1
PYTHONPATH=. .venv/bin/pytest -q
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/restore_check \
  --strict --release-hold HOLD
```

## Safety
release_hold = HOLD. Always create backup before restoring. Verify test suite at target state.
