# Frozen Backlog Human Approval Policy

**Task:** T1266
**Status:** release_hold = HOLD
**Scope:** All 22 frozen backlog files

## Purpose

Define human approval requirements for promoting frozen files
out of HOLD state into tracked repository.

## Approval Gates

### Gate 1: Risk Classification Review
- Human confirms risk classification (HIGH/MEDIUM)
- Human acknowledges side-effect inventory
- Human signs off on inspection report (T1265)

### Gate 2: Evidence Validation
- Human reviews evidence packet (T1267)
- Human confirms completeness
- Human approves evidence artifact

### Gate 3: Promotion Decision
- Human explicitly approves promotion (T1268)
- Human confirms rollback plan exists (T1269)
- Human authorizes commit

## Approval Artifact Format

```
APPROVAL: <filename>
RISK_CLASS: HIGH | MEDIUM
GATES_PASSED: [1, 2, 3]
HUMAN_ID: <identifier>
TIMESTAMP: <ISO8601>
NOTES: <optional>
```

## Approval Authority

- Only human reviewers may approve promotion
- Agent cannot self-approve any frozen file
- Approval is per-file, not batch
- Approval may be conditional on additional requirements

## Revocation

- Human may revoke approval at any time before commit
- Revocation returns file to HOLD state
- Revocation reason must be documented
