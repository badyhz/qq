# Failed Full Suite Recovery

## Symptoms
- `PYTHONPATH=. .venv/bin/pytest -q` shows failures
- Some tests error or fail
- Test count changes unexpectedly

## Likely Causes
- Code change introduced regression
- Missing dependency
- Fixture data changed
- Environment issue
- New test added but code not updated

## Commands to Inspect
```bash
# Run with verbose output
PYTHONPATH=. .venv/bin/pytest -v 2>&1 | tail -50

# Run only failing tests
PYTHONPATH=. .venv/bin/pytest -x -v 2>&1 | head -100

# Check which test files are affected
PYTHONPATH=. .venv/bin/pytest --collect-only 2>&1 | grep "ERROR"

# Check git status for unexpected changes
git status --short
git diff --stat
```

## Safe Recovery Commands
```bash
# If specific test file is failing, run it in isolation
PYTHONPATH=. .venv/bin/pytest tests/unit/test_offline_research_experiment_library.py -v

# If import error, check sys.path
python3 -c "import sys; print(sys.path)"

# If fixture missing, check fixtures
ls tests/fixtures/

# Re-run full suite after fix
PYTHONPATH=. .venv/bin/pytest -q
```

## Forbidden Recovery Commands
- Do not delete failing tests
- Do not skip failing tests with `--ignore`
- Do not modify test expectations to match broken code
- Do not force-pass tests

## Escalation Rule
If full suite fails:
1. Identify the specific failure
2. Check if it is a code regression or test issue
3. Fix the root cause
4. Re-run full suite
5. If persistent, escalate with full error output

## Final Verification
```bash
# Full suite must pass
PYTHONPATH=. .venv/bin/pytest -q
# Expected: X passed, Y skipped, 0 failed
```

## Safety
release_hold = HOLD. Advisory only. Human review required. Do not proceed with failing tests.
