# Run Human Review Packet Only

## Purpose
Build and validate the human review packet from existing pipeline outputs.

## Prerequisites
- Quality gate results in `/tmp/multi_strategy_research_quality_gate/`
- Artifact browser results in `/tmp/research_artifact_browser/`
- Comparison results in `/tmp/research_comparison_analytics/`
- release_hold = HOLD

## Commands
```bash
# Build packet
python3 scripts/build_research_human_review_packet.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --artifact-browser-dir /tmp/research_artifact_browser \
  --comparison-dir /tmp/research_comparison_analytics \
  --output-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD

# Validate packet
python3 scripts/validate_research_human_review_packet.py \
  --review-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

## Expected Outputs
- `/tmp/research_human_review_packet/review_packet.json`
- `/tmp/research_human_review_packet/review_checklist.json`
- `/tmp/research_human_review_packet/review_signoff_template.json`
- `/tmp/research_human_review_packet/review_audit_trail.json`
- `/tmp/research_human_review_packet/human_review_report.md`
- `/tmp/research_human_review_packet/human_review_report.html`

## PASS Criteria
- Both commands exit 0
- Validation passes
- All review artifacts generated
- release_hold = HOLD

## FAIL Criteria
- Build or validate fails
- Missing artifacts
- Safety flags incorrect

## Safety Notes
- Advisory only
- Human review required
- Allowed decisions: REJECT, REQUEST_MORE_RESEARCH, ACCEPT_ADVISORY_RESEARCH_ONLY
- Forbidden decisions: APPROVE_LIVE, APPROVE_TESTNET_SUBMIT, APPROVE_RUNTIME

## Forbidden Actions
- Do not change release-hold
- Do not auto-approve
- Do not skip validation

## Recovery Path
See `docs/recovery/missing_review_packet_recovery.md` and `docs/recovery/recover_from_failed_human_review.md`
