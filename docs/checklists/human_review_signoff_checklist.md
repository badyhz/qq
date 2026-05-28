# Human Review Signoff Checklist

## CL-HRS-001: Review Packet Exists
- **ID:** CL-HRS-001
- **Required:** Required
- **Evidence path:** `/tmp/research_human_review_packet/review_packet.json`
- **Pass condition:** Valid JSON review packet
- **Fail condition:** Missing or invalid
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-002: Review Checklist Complete
- **ID:** CL-HRS-002
- **Required:** Required
- **Evidence path:** `/tmp/research_human_review_packet/review_checklist.json`
- **Pass condition:** All checklist items present
- **Fail condition:** Missing items
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-003: Signoff Template Valid
- **ID:** CL-HRS-003
- **Required:** Required
- **Evidence path:** `/tmp/research_human_review_packet/review_signoff_template.json`
- **Pass condition:** Template has allowed and forbidden decisions
- **Fail condition:** Missing decision lists
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-004: Allowed Decisions Only
- **ID:** CL-HRS-004
- **Required:** Required
- **Evidence path:** Signoff template
- **Pass condition:** Only REJECT, REQUEST_MORE_RESEARCH, ACCEPT_ADVISORY_RESEARCH_ONLY
- **Fail condition:** Forbidden decisions present
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-005: No Forbidden Decisions
- **ID:** CL-HRS-005
- **Required:** Required
- **Evidence path:** Signoff template
- **Pass condition:** No APPROVE_LIVE, APPROVE_TESTNET_SUBMIT, APPROVE_RUNTIME, AUTO_PROMOTE
- **Fail condition:** Forbidden decisions present
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-006: Audit Trail Present
- **ID:** CL-HRS-006
- **Required:** Required
- **Evidence path:** `/tmp/research_human_review_packet/review_audit_trail.json`
- **Pass condition:** Audit trail exists with hashes
- **Fail condition:** Missing or no hashes
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-007: Validation Passes
- **ID:** CL-HRS-007
- **Required:** Required
- **Evidence path:** `validate_research_human_review_packet.py` output
- **Pass condition:** Validation passes
- **Fail condition:** Validation fails
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-008: release_hold = HOLD
- **ID:** CL-HRS-008
- **Required:** Required
- **Evidence path:** Review manifest
- **Pass condition:** release_hold = HOLD
- **Fail condition:** release_hold != HOLD
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-009: Advisory Only Confirmed
- **ID:** CL-HRS-009
- **Required:** Required
- **Evidence path:** Review packet
- **Pass condition:** advisory_only = true
- **Fail condition:** advisory_only != true
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-HRS-010: Human Signs Off
- **ID:** CL-HRS-010
- **Required:** Required
- **Evidence path:** Signoff decision
- **Pass condition:** Human selects allowed decision
- **Fail condition:** No decision or forbidden decision
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## Safety Reminder
Human review signoff must use allowed decisions only. release_hold = HOLD. Advisory only. No auto-promotion.
