# Recover from Failed Artifact Browser

## Purpose
Recover when artifact browser build fails.

## Prerequisites
- Quality gate results exist
- release_hold = HOLD

## Commands
```bash
# Check if quality gate output exists
ls -la /tmp/multi_strategy_research_quality_gate/

# Check error output
python3 scripts/build_research_artifact_browser.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output-dir /tmp/research_artifact_browser \
  --strict --release-hold HOLD 2>&1 | tee /tmp/artifact_browser_error.log

# If quality gate output missing, re-run quality gate
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --deterministic-seed 424242 --strict --release-hold HOLD

# Re-run artifact browser
python3 scripts/build_research_artifact_browser.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output-dir /tmp/research_artifact_browser \
  --strict --release-hold HOLD
```

## Expected Outputs
- `/tmp/research_artifact_browser/artifact_index.json`
- `/tmp/research_artifact_browser/browser_report.html`

## PASS Criteria
- Browser builds successfully
- All artifacts generated

## FAIL Criteria
- Build still fails after recovery
- Quality gate output corrupted

## Safety Notes
- Offline only
- Advisory only
- release_hold = HOLD

## Forbidden Actions
- Do not change release-hold
- Do not skip quality gate
- Do not use corrupted data

## Recovery Path
If recovery fails:
1. Check quality gate output integrity
2. Re-run full pipeline from workbench
3. See `docs/recovery/missing_quality_artifacts_recovery.md`
