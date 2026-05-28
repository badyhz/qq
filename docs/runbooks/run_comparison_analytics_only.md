# Run Comparison Analytics Only

## Purpose
Run comparison analytics on existing artifact browser results.

## Prerequisites
- Artifact browser results in `/tmp/research_artifact_browser/`
- release_hold = HOLD

## Commands
```bash
python3 scripts/build_research_comparison_analytics.py \
  --bundle baseline=/tmp/research_artifact_browser \
  --bundle candidate=/tmp/research_artifact_browser \
  --output-dir /tmp/research_comparison_analytics \
  --strict --release-hold HOLD
```

## Expected Outputs
- `/tmp/research_comparison_analytics/comparison_report.json`
- `/tmp/research_comparison_analytics/quality_series.json`
- `/tmp/research_comparison_analytics/scorecard.json`
- `/tmp/research_comparison_analytics/comparison_report.md`

## PASS Criteria
- Exit code 0
- All comparison artifacts generated
- No regressions detected

## FAIL Criteria
- Non-zero exit code
- Missing comparison artifacts

## Safety Notes
- Uses --strict --release-hold HOLD
- Advisory only
- Human review required

## Forbidden Actions
- Do not change release-hold
- Do not auto-approve comparisons

## Recovery Path
See `docs/recovery/recover_from_failed_comparison.md`
