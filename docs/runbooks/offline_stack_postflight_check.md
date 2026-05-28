# Offline Stack Postflight Check

## Purpose
Validate outputs after running the offline pipeline.

## Prerequisites
- Pipeline completed
- release_hold = HOLD

## Commands
```bash
# Check outputs exist
test -d /tmp/multi_strategy_research_workbench && echo "workbench: OK" || echo "workbench: MISSING"
test -d /tmp/multi_strategy_research_quality_gate && echo "quality_gate: OK" || echo "quality_gate: MISSING"
test -d /tmp/research_artifact_browser && echo "browser: OK" || echo "browser: MISSING"
test -d /tmp/research_comparison_analytics && echo "comparison: OK" || echo "comparison: MISSING"
test -d /tmp/research_human_review_packet && echo "review: OK" || echo "review: MISSING"

# Check key artifacts
test -f /tmp/multi_strategy_research_quality_gate/manifest.json && echo "manifest: OK" || echo "manifest: MISSING"
test -f /tmp/research_human_review_packet/review_packet.json && echo "review_packet: OK" || echo "review_packet: MISSING"

# Validate release_hold in manifests
python3 -c "
import json
m = json.load(open('/tmp/multi_strategy_research_quality_gate/manifest.json'))
assert m.get('release_hold') == 'HOLD', f'Expected HOLD, got {m.get(\"release_hold\")}'
print('quality_gate release_hold: HOLD')
"

# Validate review packet
python3 scripts/validate_research_human_review_packet.py \
  --review-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD

# Run full test suite
PYTHONPATH=. .venv/bin/pytest -q

# Run governance validation
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/postflight_governance \
  --strict --release-hold HOLD

# Check git status
git status --short
```

## Expected Outputs
- All pipeline outputs exist
- All key artifacts present
- release_hold = HOLD in all manifests
- Review packet validation: PASS
- Full test suite: PASS
- Governance: PASS

## PASS Criteria
- All outputs exist
- All validations pass
- release_hold = HOLD everywhere
- No unwanted staged files

## FAIL Criteria
- Missing outputs
- Validation failures
- release_hold != HOLD
- Unwanted files staged

## Safety Notes
- This confirms the pipeline produced valid, safe outputs
- Do not promote results if postflight fails
- release_hold = HOLD

## Forbidden Actions
- Do not skip postflight
- Do not promote on failure
- Do not change release-hold

## Recovery Path
If postflight fails:
1. Identify specific failure
2. See relevant recovery doc
3. Re-run failed stage
4. Re-run postflight
