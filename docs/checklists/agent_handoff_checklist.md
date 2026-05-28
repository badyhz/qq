# Agent Handoff Checklist

## CL-AH-001: Documentation Complete
- **ID:** CL-AH-001
- **Required:** Required
- **Evidence path:** `docs/operator_manuals/`
- **Pass condition:** All 7 operator manuals present
- **Fail condition:** Missing manuals
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-002: Runbooks Complete
- **ID:** CL-AH-002
- **Required:** Required
- **Evidence path:** `docs/runbooks/`
- **Pass condition:** All 13 runbooks present
- **Fail condition:** Missing runbooks
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-003: Checklists Complete
- **ID:** CL-AH-003
- **Required:** Required
- **Evidence path:** `docs/checklists/`
- **Pass condition:** All 10 checklists present
- **Fail condition:** Missing checklists
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-004: Recovery Docs Complete
- **ID:** CL-AH-004
- **Required:** Required
- **Evidence path:** `docs/recovery/`
- **Pass condition:** All 9 recovery docs present
- **Fail condition:** Missing recovery docs
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-005: Experiment Library
- **ID:** CL-AH-005
- **Required:** Required
- **Evidence path:** `tests/fixtures/offline_research_experiment_library/experiment_catalog.json`
- **Pass condition:** 20+ experiments validated
- **Fail condition:** Missing or invalid catalog
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-006: Governance Validator
- **ID:** CL-AH-006
- **Required:** Required
- **Evidence path:** `scripts/validate_offline_research_stack_docs.py`
- **Pass condition:** Validator exists and passes
- **Fail condition:** Validator missing or fails
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-007: Test Suite Passing
- **ID:** CL-AH-007
- **Required:** Required
- **Evidence path:** pytest output
- **Pass condition:** Full suite passes (0 failures)
- **Fail condition:** Any failure
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-008: Untracked Warning
- **ID:** CL-AH-008
- **Required:** Required
- **Evidence path:** Operator manual
- **Pass condition:** Untracked external state warning present
- **Fail condition:** Warning missing
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-009: Safety Manual
- **ID:** CL-AH-009
- **Required:** Required
- **Evidence path:** `docs/operator_manuals/offline_research_stack_safety_manual.md`
- **Pass condition:** Safety manual complete with all sections
- **Fail condition:** Safety manual missing or incomplete
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-AH-010: Next Agent Knows Safety
- **ID:** CL-AH-010
- **Required:** Required
- **Evidence path:** Handoff communication
- **Pass condition:** Next agent acknowledges safety rules
- **Fail condition:** Safety rules not communicated
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## Safety Reminder
Agent handoff must preserve all safety boundaries. Next agent must understand: release_hold = HOLD, offline only, advisory only, human review required, no auto-promotion.
