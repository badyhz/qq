# Offline Stack Preflight Check

## Purpose
Validate environment and prerequisites before running the offline pipeline.

## Prerequisites
- Python 3.10+
- Virtual environment set up
- release_hold = HOLD

## Commands
```bash
# Check Python version
python3 --version

# Check virtual environment
test -d .venv && echo "venv exists" || echo "venv missing"

# Check fixtures
test -d tests/fixtures/historical_backtest_lab && echo "fixtures exist" || echo "fixtures missing"

# Check experiment catalog
test -f tests/fixtures/offline_research_experiment_library/experiment_catalog.json && echo "catalog exists" || echo "catalog missing"

# Validate governance
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/preflight_governance \
  --strict --release-hold HOLD

# Validate experiment library
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/preflight_experiment \
  --strict --release-hold HOLD

# Run quick test subset
PYTHONPATH=. .venv/bin/pytest tests/unit/test_research_safety_regression*.py -q

# Check git status
git status --short
```

## Expected Outputs
- Python 3.10+
- Virtual environment exists
- Fixtures exist
- Catalog exists
- Governance validation: PASS
- Experiment library validation: PASS
- Safety tests: PASS
- Git status clean (no unwanted staged files)

## PASS Criteria
- All checks pass
- No safety violations
- No unwanted staged files

## FAIL Criteria
- Missing prerequisites
- Governance validation fails
- Experiment validation fails
- Safety tests fail
- Unwanted files staged

## Safety Notes
- This is a gate check
- Do not proceed if preflight fails
- release_hold = HOLD

## Forbidden Actions
- Do not skip preflight
- Do not proceed on failure
- Do not change release-hold

## Recovery Path
If preflight fails:
1. Fix the specific issue
2. Re-run preflight
3. Only proceed when all checks pass
