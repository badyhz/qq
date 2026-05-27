# Verification Script Review Overview

**Task ID:** T1281
**release_hold:** HOLD
**Status:** Active

## Scope

Defines governance policies for reviewing verification scripts in the qq project.

## In-Scope Scripts

- `scripts/verify_risk_release_flow.py` (MEDIUM-risk)
- `scripts/verify_testnet_repair_scenarios.py` (MEDIUM-risk)

## Review Objectives

1. Confirm scripts are dry-run only — zero exchange I/O
2. Confirm all dependencies are mocked or stubbed
3. Confirm no side effects on disk, network, or state files
4. Confirm high-risk imports are gated or absent
5. Confirm regression coverage exists before promotion

## Review Pipeline

```
Draft Script
  -> High-Risk Import Policy (T1282)
  -> Dry-Run Only Proof (T1283)
  -> Mocked Dependency Policy (T1284)
  -> No Side Effect Policy (T1285)
  -> Regression Requirement (T1286)
  -> Human Confirmation (T1287)
  -> Promotion Checklist (T1288)
  -> Blocked State Policy (T1289)
  -> Closeout (T1290)
```

## Governance Principles

- Verification scripts are READ-ONLY by definition
- No secrets, no exchange clients, no order submission
- Every script must prove safety before merge
- Human sign-off required for any MEDIUM-risk artifact

## References

- medium_risk_verification_script_policy.md
- no_submit_release_gate_overview.md
