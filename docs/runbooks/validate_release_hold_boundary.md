# Validate release_hold Boundary

## Purpose
Verify that release_hold = HOLD across all components and outputs.

## Prerequisites
- Pipeline outputs exist
- release_hold = HOLD

## Commands
```bash
# Check governance
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/release_hold_validation \
  --strict --release-hold HOLD

# Check experiment library
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/release_hold_exp_validation \
  --strict --release-hold HOLD

# Grep for release_hold in outputs
grep -r "release_hold" /tmp/multi_strategy_research_quality_gate/manifest.json
grep -r "release_hold" /tmp/research_human_review_packet/review_manifest.json 2>/dev/null || true

# Run safety regression tests
PYTHONPATH=. .venv/bin/pytest tests/unit/test_research_safety_regression*.py -q
```

## Expected Outputs
- Governance validation: PASS
- Experiment library validation: PASS
- All manifests show release_hold = HOLD
- Safety regression tests pass

## PASS Criteria
- All validations pass
- All manifests show HOLD
- Safety tests pass

## FAIL Criteria
- Any validation fails
- Any manifest shows non-HOLD
- Safety tests fail

## Safety Notes
- This is the most critical safety check
- release_hold must be HOLD everywhere
- Any deviation is a safety violation

## Forbidden Actions
- Do not change release_hold
- Do not skip any check
- Do not override safety failures

## Recovery Path
If release_hold is not HOLD:
1. STOP immediately
2. Do not proceed
3. Escalate to human operator
4. See `docs/recovery/invalid_safety_flags_recovery.md`
