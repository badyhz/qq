# Bad Commit Recovery

## Symptoms
- Commit includes unwanted files
- Commit message is incorrect
- Commit includes external state
- Commit breaks test suite

## Likely Causes
- Used `git add .`
- Wrong files staged
- Commit message typo
- Code regression committed

## Commands to Inspect
```bash
# Check last commit
git log --oneline -5

# Check what was in last commit
git show --stat HEAD

# Check if forbidden files were committed
git show --name-only HEAD | grep -E "(live_runner|live_playbook|run_|submit_|verify_)" && echo "FORBIDDEN FILES COMMITTED" || echo "Clean"

# Check if test suite still passes
PYTHONPATH=. .venv/bin/pytest -q
```

## Safe Recovery Commands
```bash
# If commit is the most recent and not pushed:
# Undo commit, keep changes staged
git reset --soft HEAD~1

# Unstage everything
git reset HEAD

# Re-stage correctly
# git add <specific files>

# Re-commit
# git commit -m "correct message"

# If commit was pushed (to non-main branch):
# Create a revert commit
# git revert HEAD
```

## Forbidden Recovery Commands
- Do not force-push to main
- Do not `git reset --hard` without backup
- Do not delete git history
- Do not amend pushed commits

## Escalation Rule
If bad commit was pushed to main:
1. Do not force-push
2. Create revert commit
3. If external state was pushed, escalate immediately
4. May need to rotate any accidentally exposed credentials

## Final Verification
```bash
# Verify last commit is clean
git show --name-only HEAD | grep -E "(live_runner|live_playbook|run_|submit_|verify_)" && echo "FAIL" || echo "PASS"

# Verify test suite
PYTHONPATH=. .venv/bin/pytest -q
```

## Safety
release_hold = HOLD. Never force-push to main. Always verify commits before pushing.
