# Engineering Closeout Bundle

## Purpose

Standardized closeout pipeline for phase/milestone completions. Ensures clean git state, proper tagging, and frozen boundary integrity.

---

## Pipeline Stages

### PRE_CLOSEOUT

Verify prerequisites before starting closeout.

```bash
# 1. Verify inside git repo
git rev-parse --is-inside-work-tree

# 2. Check current HEAD
git log --oneline -1

# 3. Verify no staged changes
git diff --cached --name-only

# 4. Check existing tags
git tag -l '{phase}*'
```

**Gate:** All checks pass before proceeding.

### SCOPED_CLASSIFY

Classify dirty tree into categories.

```bash
# Full dirty tree
git status --short

# Count by type
git status --short | grep -c "^??"  # untracked
git status --short | grep -c "^ M"  # modified-unstaged
git status --short | grep -c "^M "  # modified-staged
```

**Categories:**
| Category | Action | Example |
|----------|--------|---------|
| Phase work (modified) | STAGE | guard-injected scripts |
| Phase work (untracked) | STAGE | new test files, new docs |
| Frozen files | EXCLUDE | 22 frozen scripts, core/live_runner.py |
| Local junk | EXCLUDE | .sh scripts, .swp files |
| Unrelated work | EXCLUDE | automation/, other features |

### FROZEN_EXCLUSION

Verify no frozen files in staging area.

```bash
# Known frozen patterns
FROZEN_PATTERNS="live_runner|live_playbook|submit_approved|submit_replayed|run_replay_submit|safe_flatten|run_spot_testnet|run_testnet_order|verify_testnet_repair|replay_shadow|run_controlled|run_daily_shadow|run_next_shadow|run_observation|run_remediation|run_right_breakout|run_shadow|run_signal"

# Check staged files
git diff --cached --name-only | grep -E "$FROZEN_PATTERNS"
# Should return empty (no frozen files staged)
```

**Gate:** No frozen files staged. If found → STOP, unstage them.

### SCOPED_STAGE

Stage ONLY phase-related files. NEVER use `git add .` or `git add -A`.

```bash
# Stage specific categories
git add scripts/{phase_specific_scripts}.py
git add tests/unit/test_{phase_specific}_guard.py
git add docs/{phase_specific_docs}.md

# Verify staging
git diff --cached --stat
```

**Rules:**
- Explicit file paths only
- No wildcards that could catch frozen files
- Verify staging before commit

### COMMIT

Create closure commit with descriptive message.

```bash
git commit -m "$(cat <<'EOF'
feat: complete {phase} guard integration ({count}/{total}, {coverage}% coverage)

{description}

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

**Rules:**
- Descriptive message with metrics
- Co-author attribution
- No generic messages

### TAG

Move or create closure tag.

```bash
# If tag exists, delete and recreate
git tag -d {phase}-complete
git tag {phase}-complete

# If tag doesn't exist
git tag {phase}-complete
```

**Rules:**
- Delete + recreate (not force move) for clarity
- Tag must point to closure commit

### VERIFY

Final integrity verification.

```bash
# 1. Tag points to HEAD
git show {phase}-complete --quiet --format="%H"
git rev-parse HEAD
# Should match

# 2. Working tree state
git status --short
# Should show only frozen/junk files

# 3. Commit content
git log --oneline -1
# Should show closure commit

# 4. No frozen files committed
git show --stat {phase}-complete | grep -E "$FROZEN_PATTERNS"
# Should return empty
```

**Gate:** All verifications pass. If fail → investigate before proceeding.

---

## Complete Pipeline

```bash
# PRE_CLOSEOUT
git rev-parse --is-inside-work-tree
git log --oneline -1
git diff --cached --name-only
git tag -l '{phase}*'

# SCOPED_CLASSIFY
git status --short

# FROZEN_EXCLUSION
git diff --cached --name-only | grep -E "$FROZEN_PATTERNS"

# SCOPED_STAGE
git add scripts/{files}.py tests/unit/test_{files}_guard.py docs/{files}.md
git diff --cached --stat

# COMMIT
git commit -m "feat: complete {phase} ({count}/{total}, {coverage}%)"

# TAG
git tag -d {phase}-complete 2>/dev/null
git tag {phase}-complete

# VERIFY
git show {phase}-complete --quiet --format="%H"
git rev-parse HEAD
git status --short
git log --oneline -1
```

---

## Rollback

To revert to pre-closeout state:

```bash
# Delete closure tag
git tag -d {phase}-complete

# Reset to pre-closeout commit
git reset --hard {pre-closeout-commit}
```

---

## Failure Modes

| Failure | Cause | Fix |
|---------|-------|-----|
| Tag already exists | Previous closeout | Delete + recreate |
| Frozen file staged | Wrong git add | Unstage it |
| Dirty tree after closeout | Missing files | Add them, amend commit |
| Tag points to wrong commit | Race condition | Delete + recreate |

---

## Example (Phase2)

```bash
# PRE_CLOSEOUT
git rev-parse --is-inside-work-tree  # → true
git log --oneline -1  # → 71e34ca docs: record phase2 safe batch completion
git tag -l 'phase2*'  # → phase2-complete

# SCOPED_CLASSIFY
git status --short  # → 39 modified, 83 untracked

# FROZEN_EXCLUSION
# No frozen files in modified list

# SCOPED_STAGE
git add scripts/ tests/ docs/  # explicit paths
git diff --cached --stat  # → 97 files, 5955 insertions

# COMMIT
git commit -m "feat: complete execution guard phase2 integration (41/41, 100% coverage)"
# → f391b8b

# TAG
git tag -d phase2-complete  # → deleted (was 71e34ca)
git tag phase2-complete  # → created at f391b8b

# VERIFY
git show phase2-complete --quiet --format="%H"  # → f391b8b
git rev-parse HEAD  # → f391b8b
git status --short  # → only frozen/junk files remain
```
