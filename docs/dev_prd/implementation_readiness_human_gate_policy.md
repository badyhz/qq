# T1195 - Implementation Readiness Human Gate Policy

## Gates

### APPROVAL_GATE
- **Required Evidence:** Readiness score report, blocker status, test results
- **Approval Chain:** Single authorized approver
- **Trigger:** Task completion, readiness score above threshold

### REVIEW_GATE
- **Required Evidence:** Diff review, risk assessment, regression results
- **Approval Chain:** Peer reviewer + technical lead
- **Trigger:** Wave transition, high-risk change

### RELEASE_GATE
- **Required Evidence:** Full test suite, performance baseline, rollback plan, security review
- **Approval Chain:** Technical lead + project owner
- **Trigger:** Production deployment readiness

## Rules

- No gate bypassed without explicit authority override
- All gate decisions recorded with evidence
- Approval chain cannot be shortened
- Stale approvals (>30 days) require re-approval
