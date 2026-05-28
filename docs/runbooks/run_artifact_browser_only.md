# Run Artifact Browser Only

## Purpose
Build the artifact browser from existing quality gate results.

## Prerequisites
- Quality gate results in `/tmp/multi_strategy_research_quality_gate/`
- release_hold = HOLD

## Commands
```bash
python3 scripts/build_research_artifact_browser.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output-dir /tmp/research_artifact_browser \
  --strict --release-hold HOLD
```

## Expected Outputs
- `/tmp/research_artifact_browser/artifact_index.json`
- `/tmp/research_artifact_browser/browser_report.html`

## PASS Criteria
- Exit code 0
- Artifact index generated
- Browser report generated

## FAIL Criteria
- Non-zero exit code
- Missing output files

## Safety Notes
- Uses --strict --release-hold HOLD
- Advisory only
- Human review required

## Forbidden Actions
- Do not change release-hold
- Do not skip validation

## Recovery Path
See `docs/recovery/recover_from_failed_artifact_browser.md`
