# New Experiment Intake Checklist

## CL-NEI-001: Experiment ID Unique
- **ID:** CL-NEI-001
- **Required:** Required
- **Evidence path:** `experiment_catalog.json`
- **Pass condition:** experiment_id not already in catalog
- **Fail condition:** Duplicate experiment_id
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-002: Required Fields Present
- **ID:** CL-NEI-002
- **Required:** Required
- **Evidence path:** Experiment definition JSON
- **Pass condition:** All 16 required fields present
- **Fail condition:** Missing fields
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-003: Safety Flags Complete
- **ID:** CL-NEI-003
- **Required:** Required
- **Evidence path:** `safety_flags` in experiment definition
- **Pass condition:** All 9 safety flags present and correct
- **Fail condition:** Missing or incorrect flags
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-004: release_hold = HOLD
- **ID:** CL-NEI-004
- **Required:** Required
- **Evidence path:** `safety_flags.release_hold`
- **Pass condition:** Value = "HOLD"
- **Fail condition:** Value != "HOLD"
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-005: advisory_only = true
- **ID:** CL-NEI-005
- **Required:** Required
- **Evidence path:** `safety_flags.advisory_only`
- **Pass condition:** Value = true
- **Fail condition:** Value != true
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-006: human_review_required = true
- **ID:** CL-NEI-006
- **Required:** Required
- **Evidence path:** `safety_flags.human_review_required`
- **Pass condition:** Value = true
- **Fail condition:** Value != true
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-007: No Forbidden Commands
- **ID:** CL-NEI-007
- **Required:** Required
- **Evidence path:** `allowed_commands`
- **Pass condition:** No forbidden commands in allowed list
- **Fail condition:** Forbidden command found
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-008: No Forbidden Strings
- **ID:** CL-NEI-008
- **Required:** Required
- **Evidence path:** Entire experiment definition
- **Pass condition:** No forbidden live/testnet/runtime strings
- **Fail condition:** Forbidden string found
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-009: Offline Commands Only
- **ID:** CL-NEI-009
- **Required:** Required
- **Evidence path:** `allowed_commands`
- **Pass condition:** All commands are offline research commands
- **Fail condition:** Live/testnet/runtime command present
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-NEI-010: Validation Passes
- **ID:** CL-NEI-010
- **Required:** Required
- **Evidence path:** `validate_offline_research_experiment_library.py` output
- **Pass condition:** Validation passes with new experiment
- **Fail condition:** Validation fails
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## Safety Reminder
New experiments must be offline/advisory only. release_hold = HOLD. No forbidden commands or strings. Validation must pass.
