# Untracked External State Recovery

## Symptoms
- Untracked live/testnet/shadow files accidentally staged
- `git add .` used instead of explicit add
- Forbidden files in staging area
- Commit would include external state

## Likely Causes
- Used `git add .` or `git add -A`
- Did not check `git status` before staging
- Accidental staging of untracked files

## Commands to Inspect
```bash
# Check what's staged
git diff --cached --stat

# Check untracked files
git status --short

# List known untracked files
ls core/live_runner.py scripts/live_playbook.py scripts/run_*.py scripts/safe_flatten*.py scripts/submit_*.py scripts/verify_*.py 2>/dev/null
```

## Safe Recovery Commands
```bash
# Unstage all files
git reset HEAD

# Stage only specific files (example)
# git add docs/operator_manuals/offline_research_stack_operator_manual.md
# git add core/offline_research_experiment_library.py
# git add tests/unit/test_offline_research_experiment_library.py

# Verify staging is correct
git diff --cached --stat
git status --short
```

## Forbidden Recovery Commands
- Do not use `git add .`
- Do not use `git add -A`
- Do not stage core/live_runner.py
- Do not stage scripts/live_playbook.py
- Do not stage any scripts/run_*.py (testnet/shadow)
- Do not stage scripts/submit_*.py
- Do not stage scripts/verify_risk_release_flow.py
- Do not stage scripts/verify_testnet_repair_scenarios.py
- Do not stage research/ directory

## Escalation Rule
If external state was committed:
1. Do not push
2. `git reset HEAD~1` to undo commit
3. Re-stage correctly with explicit `git add`
4. Re-commit
5. If already pushed, escalate immediately

## Final Verification
```bash
# Verify no forbidden files staged
git diff --cached --name-only | grep -E "(live_runner|live_playbook|run_controlled|run_daily|run_next|run_observation|run_remediation|run_replay|run_right_breakout|run_shadow|run_signal|run_spot|run_testnet|safe_flatten|submit_|verify_risk|verify_testnet)" && echo "FAIL: Forbidden files staged" || echo "PASS: No forbidden files"
```

## Safety
release_hold = HOLD. Never stage untracked live/testnet/shadow files. Use explicit git add only.
