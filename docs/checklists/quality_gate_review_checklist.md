# Quality Gate Review Checklist

## CL-QG-001: Quality Gate Verdict
- **ID:** CL-QG-001
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/quality_gate.json`
- **Pass condition:** verdict = PASS
- **Fail condition:** verdict != PASS
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-002: Safety Flags Present
- **ID:** CL-QG-002
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/manifest.json`
- **Pass condition:** All 9 safety flags present and correct
- **Fail condition:** Missing or incorrect safety flags
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-003: release_hold = HOLD
- **ID:** CL-QG-003
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/manifest.json`
- **Pass condition:** release_hold = "HOLD"
- **Fail condition:** release_hold != "HOLD"
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-004: OOS Splits
- **ID:** CL-QG-004
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/quality_gate.json`
- **Pass condition:** oos_splits >= 3
- **Fail condition:** oos_splits < 3
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-005: Stability Score
- **ID:** CL-QG-005
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/quality_gate.json`
- **Pass condition:** stability_score >= 0.60
- **Fail condition:** stability_score < 0.60
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-006: Parameter Fragility
- **ID:** CL-QG-006
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/quality_gate.json`
- **Pass condition:** parameter_fragility <= 0.40
- **Fail condition:** parameter_fragility > 0.40
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-007: Negative Control
- **ID:** CL-QG-007
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/quality_gate.json`
- **Pass condition:** negative_control_margin >= 0.10
- **Fail condition:** negative_control_margin < 0.10
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-008: Reproducibility
- **ID:** CL-QG-008
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/quality_gate.json`
- **Pass condition:** reproducibility = true
- **Fail condition:** reproducibility = false
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-009: Advisory Only
- **ID:** CL-QG-009
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/manifest.json`
- **Pass condition:** advisory_only = true
- **Fail condition:** advisory_only != true
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-QG-010: Human Review Required
- **ID:** CL-QG-010
- **Required:** Required
- **Evidence path:** `/tmp/multi_strategy_research_quality_gate/manifest.json`
- **Pass condition:** human_review_required = true
- **Fail condition:** human_review_required != true
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## Safety Reminder
Quality gate review must confirm all safety boundaries. release_hold = HOLD. Advisory only. Human review required.
