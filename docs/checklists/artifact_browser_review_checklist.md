# Artifact Browser Review Checklist

## CL-AB-001: Browser Output Exists
- **ID:** CL-AB-001
- **Required:** Required
- **Evidence path:** `/tmp/research_artifact_browser/`
- **Pass condition:** Directory exists with index and report
- **Fail condition:** Directory missing or incomplete
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AB-002: Artifact Index
- **ID:** CL-AB-002
- **Required:** Required
- **Evidence path:** `/tmp/research_artifact_browser/artifact_index.json`
- **Pass condition:** Valid JSON with artifact catalog
- **Fail condition:** Missing or invalid JSON
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AB-003: Browser Report
- **ID:** CL-AB-003
- **Required:** Required
- **Evidence path:** `/tmp/research_artifact_browser/browser_report.html`
- **Pass condition:** Standalone HTML file exists
- **Fail condition:** Missing or broken HTML
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AB-004: No External Resources
- **ID:** CL-AB-004
- **Required:** Required
- **Evidence path:** `/tmp/research_artifact_browser/browser_report.html`
- **Pass condition:** No CDN, no external JS, no network references
- **Fail condition:** External resources detected
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AB-005: release_hold in Output
- **ID:** CL-AB-005
- **Required:** Required
- **Evidence path:** Browser report content
- **Pass condition:** release_hold = HOLD mentioned
- **Fail condition:** release_hold not mentioned
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## Safety Reminder
Artifact browser must be self-contained offline. No external resources. release_hold = HOLD.
