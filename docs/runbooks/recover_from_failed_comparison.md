# Recover from Failed Comparison

## Purpose
Recover when comparison analytics build fails.

## Prerequisites
- Artifact browser results exist
- release_hold = HOLD

## Commands
```bash
# Check if artifact browser output exists
ls -la /tmp/research_artifact_browser/

# Check error
python3 scripts/build_research_comparison_analytics.py \
  --bundle baseline=/tmp/research_artifact_browser \
  --bundle candidate=/tmp/research_artifact_browser \
  --output-dir /tmp/research_comparison_analytics \
  --strict --release-hold HOLD 2>&1 | tee /tmp/comparison_error.log

# If artifact browser output missing, re-run
python3 scripts/build_research_artifact_browser.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output-dir /tmp/research_artifact_browser \
  --strict --release-hold HOLD

# Re-run comparison
python3 scripts/build_research_comparison_analytics.py \
  --bundle baseline=/tmp/research_artifact_browser \
  --bundle candidate=/tmp/research_artifact_browser \
  --output-dir /tmp/research_comparison_analytics \
  --strict --release-hold HOLD
```

## Expected Outputs
- `/tmp/research_comparison_analytics/comparison_report.json`
- `/tmp/research_comparison_analytics/scorecard.json`

## PASS Criteria
- Comparison builds successfully
- All artifacts generated

## FAIL Criteria
- Build still fails after recovery
- Input data corrupted

## Safety Notes
- Offline only
- Advisory only
- release_hold = HOLD

## Forbidden Actions
- Do not change release-hold
- Do not skip input validation

## Recovery Path
If recovery fails:
1. Re-run artifact browser
2. Re-run comparison
3. See `docs/recovery/recover_from_failed_comparison.md`
