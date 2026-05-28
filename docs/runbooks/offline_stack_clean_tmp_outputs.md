# Offline Stack Clean Tmp Outputs

## Purpose
Clean temporary output directories before a fresh pipeline run.

## Prerequisites
- No active pipeline running
- release_hold = HOLD

## Commands
```bash
# Remove previous outputs (if they exist)
rm -rf /tmp/multi_strategy_research_workbench
rm -rf /tmp/multi_strategy_research_quality_gate
rm -rf /tmp/research_artifact_browser
rm -rf /tmp/research_comparison_analytics
rm -rf /tmp/research_human_review_packet
rm -rf /tmp/offline_research_experiment_library_validation
rm -rf /tmp/offline_research_governance_validation
rm -rf /tmp/offline_research_operator_bundle
rm -rf /tmp/reproducibility_run1
rm -rf /tmp/reproducibility_run2

# Verify clean
ls /tmp/multi_strategy_research_* 2>/dev/null && echo "NOT CLEAN" || echo "CLEAN"
```

## Expected Outputs
- All /tmp directories removed
- Verification shows "CLEAN"

## PASS Criteria
- All directories removed
- No residual outputs

## FAIL Criteria
- Directories still exist
- Permission errors

## Safety Notes
- Only removes /tmp outputs
- Does not affect source code or fixtures
- release_hold = HOLD

## Forbidden Actions
- Do not remove fixture directories
- Do not remove source code
- Do not remove git history

## Recovery Path
If cleanup fails:
1. Check permissions
2. Manually remove directories
3. Re-run pipeline
