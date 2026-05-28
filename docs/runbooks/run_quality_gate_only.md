# Run Quality Gate Only

## Purpose
Run only the quality gate validation on existing workbench results.

## Prerequisites
- Workbench results in `/tmp/multi_strategy_research_workbench/`
- release_hold = HOLD

## Commands
```bash
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --min-oos-splits 3 \
  --min-stability-score 0.60 \
  --max-parameter-fragility 0.40 \
  --max-overlap-risk 0.70 \
  --min-negative-control-margin 0.10 \
  --bootstrap-iterations 200 \
  --deterministic-seed 424242 \
  --require-negative-control \
  --require-regime-breakdown \
  --require-bootstrap \
  --require-reproducibility \
  --strict --release-hold HOLD
```

## Expected Outputs
- `/tmp/multi_strategy_research_quality_gate/quality_gate.json`
- `/tmp/multi_strategy_research_quality_gate/manifest.json`
- `/tmp/multi_strategy_research_quality_gate/quality_report.md`

## PASS Criteria
- Exit code 0
- Quality gate verdict = PASS
- release_hold = HOLD in manifest

## FAIL Criteria
- Non-zero exit code
- Quality gate verdict != PASS
- Safety flags missing or incorrect

## Safety Notes
- Uses --strict --release-hold HOLD
- Advisory only output
- Human review required

## Forbidden Actions
- Do not change release-hold
- Do not skip safety checks
- Do not auto-promote

## Recovery Path
See `docs/recovery/missing_quality_artifacts_recovery.md`
