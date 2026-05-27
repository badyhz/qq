# Medium-Risk Review Overview (T1171)

## Purpose

Define the review framework for medium-risk scripts in the qq trading system.
Medium-risk scripts sit between low-risk (read-only utilities) and high-risk
(live trading, frozen boundary) modules. They require structured review but
do not need the full human-gate treatment applied to high-risk work.

## Scope

This document and the associated policy documents (T1172-T1180) apply to all
scripts classified as MEDIUM risk by the risk classifier. This includes:

- Operational scripts (run, scan, observe)
- Verification scripts (check, validate, assert)
- Shadow scripts (shadow orders, shadow scan)
- Testnet scripts (testnet dry-run, testnet smoke)
- Remediation scripts (fix, repair, restore)

## Script Types

| Type         | Example Pattern                    | Default Mode |
|--------------|------------------------------------|--------------|
| OPERATIONAL  | `run_*.py`, `scripts/run_*.py`     | dry-run      |
| VERIFICATION | `verify_*.py`, `scripts/verify_*`  | read-only    |
| SHADOW       | `run_shadow_*.py`                  | dry-run      |
| TESTNET      | `run_testnet_*.py`                 | testnet-dry  |
| REMEDIATION  | `*_repair_*.py`, `*_restore_*.py`  | dry-run      |

## Review Criteria

Every medium-risk script must satisfy:

1. **Dry-run default** - see T1174
2. **Import boundary** - see T1175
3. **Command safety** - see T1176
4. **Artifact policy** - see T1177
5. **Commit isolation** - see T1178
6. **Promotion checklist** - see T1179

## Safety Statement

Medium-risk scripts are NOT permitted to:

- Submit real orders to any exchange
- Modify frozen files
- Import from HIGH-risk modules without an abstraction layer
- Auto-commit changes
- Execute arbitrary code via eval/exec/subprocess(shell=True)
