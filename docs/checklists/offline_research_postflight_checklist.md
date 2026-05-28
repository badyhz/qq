# Offline Research Postflight Checklist

## CL-POSTFLIGHT-001: Workbench Output
- **ID:** CL-POSTFLIGHT-001
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_workbench/`
- **Pass condition:** Directory exists with workbench_results.json
- **Fail condition:** Directory missing or no results
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-002: Quality Gate Output
- **ID:** CL-POSTFLIGHT-002
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/`
- **Pass condition:** Directory exists with manifest.json showing PASS
- **Fail condition:** Directory missing or verdict != PASS
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-003: Artifact Browser Output
- **ID:** CL-POSTFLIGHT-003
- **Required:** Required
- **Evidence path:** `/tmp/research_artifact_browser/`
- **Pass condition:** Directory exists with artifact_index.json
- **Fail condition:** Directory missing or no index
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-004: Comparison Output
- **ID:** CL-POSTFLIGHT-004
- **Required:** Required
- **Evidence path:** `/tmp/research_comparison_analytics/`
- **Pass condition:** Directory exists with comparison_report.json
- **Fail condition:** Directory missing or no report
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-005: Review Packet Output
- **ID:** CL-POSTFLIGHT-005
- **Required:** Required
- **Evidence path:** `/tmp/research_human_review_packet/`
- **Pass condition:** Directory exists with review_packet.json
- **Fail condition:** Directory missing or no packet
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-006: release_hold Validation
- **ID:** CL-POSTFLIGHT-006
- **Required:** Required
- **Evidence path:** All manifest.json files
- **Pass condition:** release_hold = HOLD in all manifests
- **Fail condition:** Any manifest shows non-HOLD
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-007: Review Packet Validation
- **ID:** CL-POSTFLIGHT-007
- **Required:** Required
- **Evidence path:** `validate_research_human_review_packet.py` output
- **Pass condition:** Validation passes
- **Fail condition:** Validation fails
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-008: Full Test Suite
- **ID:** CL-POSTFLIGHT-008
- **Required:** Required
- **Evidence path:** pytest output
- **Pass condition:** All tests pass (0 failures)
- **Fail condition:** Any test failure
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-009: No Auto-Promotion
- **ID:** CL-POSTFLIGHT-009
- **Required:** Required
- **Evidence path:** Output artifacts
- **Pass condition:** No artifact contains auto-promotion authorization
- **Fail condition:** Auto-promotion detected
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-POSTFLIGHT-010: Advisory Only Confirmation
- **ID:** CL-POSTFLIGHT-010
- **Required:** Required
- **Evidence path:** Output artifacts
- **Pass condition:** All artifacts marked advisory_only = true
- **Fail condition:** Any artifact not advisory only
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## Safety Reminder
All postflight checks must pass before considering the pipeline complete. release_hold must remain HOLD. All output is advisory only.
