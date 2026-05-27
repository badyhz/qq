# Medium-Risk Commit Isolation Policy (T1178)

## Purpose

Ensure medium-risk changes are committed in isolation from high-risk
changes, so that rollback and review are straightforward.

## Rules

### R1: Never mix with HIGH-risk in same commit

A commit that includes medium-risk files must not also include
high-risk files. These must be separate commits with separate
review cycles.

### R2: Explicit file list required

Every commit containing medium-risk changes must include an explicit
file list in the commit message body. This makes it easy to verify
what was changed.

### R3: Verify no frozen files included

Before committing, verify that no frozen files (files under a freeze
boundary) are included in the staging area. Frozen files require
separate governance approval.

## Example Commit Message

```
feat: medium-risk operational scripts T1172-T1177

FILES:
- docs/dev_prd/medium_risk_operational_script_policy.md
- docs/dev_prd/medium_risk_verification_script_policy.md
- docs/dev_prd/medium_risk_dry_run_only_requirement.md
- docs/dev_prd/medium_risk_import_boundary_policy.md
- docs/dev_prd/medium_risk_command_safety_policy.md
- docs/dev_prd/medium_risk_artifact_policy.md

RISK: MEDIUM
FROZEN: none
```
