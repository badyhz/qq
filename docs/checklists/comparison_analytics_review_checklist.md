# Comparison Analytics Review Checklist

## CL-CA-001: Comparison Output Exists
- **ID:** CL-CA-001
- **Required:** Required
- **Evidence path:** `/tmp/research_comparison_analytics/`
- **Pass condition:** Directory exists with all comparison artifacts
- **Fail condition:** Directory missing or incomplete
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-CA-002: Comparison Report
- **ID:** CL-CA-002
- **Required:** Required
- **Evidence path:** `/tmp/research_comparison_analytics/comparison_report.json`
- **Pass condition:** Valid JSON with comparison results
- **Fail condition:** Missing or invalid
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-CA-003: Quality Series
- **ID:** CL-CA-003
- **Required:** Required
- **Evidence path:** `/tmp/research_comparison_analytics/quality_series.json`
- **Pass condition:** Valid JSON with quality series data
- **Fail condition:** Missing or invalid
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-CA-004: Scorecard
- **ID:** CL-CA-004
- **Required:** Required
- **Evidence path:** `/tmp/research_comparison_analytics/scorecard.json`
- **Pass condition:** Valid JSON with scorecard
- **Fail condition:** Missing or invalid
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-CA-005: No Regressions
- **ID:** CL-CA-005
- **Required:** Required
- **Evidence path:** `/tmp/research_comparison_analytics/comparison_report.json`
- **Pass condition:** No critical regressions detected
- **Fail condition:** Critical regressions present
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-CA-006: Advisory Only
- **ID:** CL-CA-006
- **Required:** Required
- **Evidence path:** Comparison report content
- **Pass condition:** Advisory only confirmed
- **Fail condition:** Not advisory only
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## Safety Reminder
Comparison analytics output is advisory only. release_hold = HOLD. No auto-promotion.
