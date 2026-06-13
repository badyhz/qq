# Human Approval Gate Report

## Status

- human_approval_required: true
- approved: false (default)
- submit_allowed: false

## Decisions

- APR_INT_001: approved=False, reason=DEFAULT_DENY: no human approval granted
- APR_INT_001: approved=False, reason=STALE_REQUEST: approval request expired
- APR_INT_001: approved=False, reason=INCOMPLETE: missing fields: price, risk_summary

## Conclusion

HUMAN_APPROVAL_GATE_VALID
DEFAULT_DENY_ENFORCED
