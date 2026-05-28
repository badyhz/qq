# Recover from Failed Human Review

## Purpose
Recover when human review packet build or validation fails.

## Prerequisites
- Quality gate, artifact browser, comparison results exist
- release_hold = HOLD

## Commands
```bash
# Check inputs
ls -la /tmp/multi_strategy_research_quality_gate/
ls -la /tmp/research_artifact_browser/
ls -la /tmp/research_comparison_analytics/

# Re-build review packet
python3 scripts/build_research_human_review_packet.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --artifact-browser-dir /tmp/research_artifact_browser \
  --comparison-dir /tmp/research_comparison_analytics \
  --output-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD

# Validate
python3 scripts/validate_research_human_review_packet.py \
  --review-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

## Expected Outputs
- `/tmp/research_human_review_packet/review_packet.json`
- Validation passes

## PASS Criteria
- Build succeeds
- Validation passes
- All safety flags correct

## FAIL Criteria
- Build or validation fails
- Safety flags incorrect
- Missing required artifacts

## Safety Notes
- Advisory only
- Human review required
- release_hold = HOLD

## Forbidden Actions
- Do not change release-hold
- Do not skip validation
- Do not auto-approve

## Recovery Path
If recovery fails:
1. Re-run upstream stages
2. See `docs/recovery/missing_review_packet_recovery.md`
