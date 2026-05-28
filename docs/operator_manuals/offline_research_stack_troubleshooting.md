# Offline Research Stack Troubleshooting

## Common Issues

### 1. Test Suite Failures

**Symptom:** `PYTHONPATH=. .venv/bin/pytest -q` shows failures
**Cause:** Missing fixtures, code changes, or environment issues
**Fix:**
1. Check which tests failed
2. Verify fixtures exist in `tests/fixtures/`
3. Re-run targeted test group
4. See `docs/recovery/failed_full_suite_recovery.md`

### 2. Quality Gate Failures

**Symptom:** Quality gate reports FAIL
**Cause:** Quality metrics below thresholds
**Fix:**
1. Check `quality_gate.json` for specific failures
2. Review threshold values
3. Check data quality in fixtures
4. See `docs/runbooks/run_quality_gate_only.md`

### 3. Missing Artifacts

**Symptom:** Expected output file not found
**Cause:** Pipeline stage failed or was skipped
**Fix:**
1. Check if previous stage completed
2. Re-run missing stage
3. See `docs/recovery/missing_quality_artifacts_recovery.md`

### 4. Corrupted JSON

**Symptom:** JSON parse error when reading artifact
**Cause:** Partial write, disk error, or interrupted process
**Fix:**
1. Identify corrupted file
2. Delete and re-generate
3. See `docs/recovery/corrupted_json_recovery.md`

### 5. Deterministic Mismatch

**Symptom:** Reproducibility check fails
**Cause:** Different seed, code change, or fixture change
**Fix:**
1. Verify deterministic seed matches
2. Check for code changes
3. Check fixture integrity
4. See `docs/recovery/reproducibility_mismatch_recovery.md`

### 6. Invalid Safety Flags

**Symptom:** Validation fails on safety flags
**Cause:** Missing or incorrect safety flags in experiment
**Fix:**
1. Check experiment definition
2. Verify all 9 required safety flags present
3. Verify release_hold = HOLD
4. See `docs/recovery/invalid_safety_flags_recovery.md`

### 7. Governance Validation Fails

**Symptom:** `validate_offline_research_stack_docs.py` returns FAIL
**Cause:** Missing docs, missing safety statements, or forbidden approvals
**Fix:**
1. Check `governance_validation.json` for specific errors
2. Add missing documentation
3. Add missing safety statements
4. Remove forbidden approval language

### 8. Experiment Library Validation Fails

**Symptom:** `validate_offline_research_experiment_library.py` returns FAIL
**Cause:** Invalid experiment definitions
**Fix:**
1. Check `experiment_library_validation.json` for errors
2. Fix invalid experiments
3. Verify safety flags
4. Remove forbidden commands/strings

### 9. Operator Bundle Build Fails

**Symptom:** `build_offline_research_operator_bundle.py` returns error
**Cause:** Missing docs or catalog
**Fix:**
1. Verify docs directory structure
2. Verify experiment catalog exists
3. Check file permissions

### 10. Git Issues

**Symptom:** Unwanted files staged or committed
**Cause:** Used `git add .` instead of explicit add
**Fix:**
1. `git reset HEAD <file>` to unstage
2. Use explicit `git add <file>` only
3. See `docs/recovery/bad_commit_recovery.md`

## Diagnostic Commands

```bash
# Check git status
git status --short

# Check what's staged
git diff --cached --stat

# Validate governance
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/offline_research_governance_validation \
  --strict --release-hold HOLD

# Validate experiment library
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_experiment_library_validation \
  --strict --release-hold HOLD

# Run full test suite
PYTHONPATH=. .venv/bin/pytest -q

# Check for forbidden imports
grep -r "import requests\|import httpx\|import aiohttp\|import binance" core/ scripts/
```

## Safety

When troubleshooting, never:
- Disable safety checks
- Change release_hold from HOLD
- Skip validation
- Force-push
- Stage untracked files
