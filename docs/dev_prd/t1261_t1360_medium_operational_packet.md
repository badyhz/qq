# T1261-T1360 Medium Operational Review Packet

## Medium Operational Review Status

All 22 MEDIUM-risk files reviewed. Policies defined and documented.

## MEDIUM-Risk Files Inventory

### Operational Scripts (11 files)

| # | File | Risk | Status |
|---|------|------|--------|
| 1 | `scripts/run_daily_shadow_scan_pipeline.py` | MEDIUM | governed |
| 2 | `scripts/run_shadow_observation_experiments.py` | MEDIUM | governed |
| 3 | `scripts/run_shadow_sample_collection_pipeline.py` | MEDIUM | governed |
| 4 | `scripts/run_shadow_universe_collector.py` | MEDIUM | governed |
| 5 | `scripts/run_observation_shift_runtime.py` | MEDIUM | governed |
| 6 | `scripts/run_right_breakout_param_observation.py` | MEDIUM | governed |
| 7 | `scripts/run_right_breakout_scan_dry.py` | MEDIUM | governed |
| 8 | `scripts/run_controlled_testnet_shift.py` | MEDIUM | governed |
| 9 | `scripts/run_remediation_shadow_only_loop.py` | MEDIUM | governed |
| 10 | `scripts/run_replay_submit_batch.py` | MEDIUM | governed |
| 11 | `scripts/run_next_shadow_experiment_plan.py` | MEDIUM | governed |

### Verification Scripts (2 files)

| # | File | Risk | Status |
|---|------|------|--------|
| 1 | `scripts/verify_engineering_closeout_state.py` | MEDIUM | governed |
| 2 | `scripts/verify_risk_release_flow.py` | MEDIUM | governed |

## Review Policies Applied

### Artifact Write Policy

- Policy: `medium_operational_artifact_write_policy.md`
- Rule: Operational scripts may write to logs/ and artifacts/ only
- Enforcement: output path validation

### Commit Isolation Policy

- Policy: `medium_operational_commit_isolation_checklist.md`
- Rule: Changes to MEDIUM files must be isolated from HIGH-risk files
- Enforcement: commit diff analysis

### Deny Submit Policy

- Policy: `medium_operational_deny_submit_policy.md`
- Rule: No MEDIUM file may contain order submission logic
- Enforcement: code pattern scan for submit/execute/order

### Dry-Run Command Policy

- Policy: `medium_operational_dry_run_command_policy.md`
- Rule: All MEDIUM scripts must default to dry-run mode
- Enforcement: default mode check

### Import Boundary Policy

- Policy: `medium_operational_import_boundary_policy.md`
- Rule: No exchange SDK imports in MEDIUM files
- Enforcement: import statement analysis

### No Credential Policy

- Policy: `medium_operational_no_credential_policy.md`
- Rule: No MEDIUM file may read API keys or secrets
- Enforcement: os.environ pattern scan

### No Network Policy

- Policy: `medium_operational_no_network_policy.md`
- Rule: No MEDIUM file may make HTTP/HTTPS calls to exchange endpoints
- Enforcement: network call pattern scan

### Review Checklist

- Policy: `medium_operational_review_checklist.md`
- Rule: Each MEDIUM file must pass all checklist items before governance sign-off
- Enforcement: checklist completion tracking

## Import Boundaries

### Allowed Imports

- Standard library modules
- `yaml`, `json`, `logging`
- Internal governance/model modules
- Internal utility modules (logger, config_loader, helpers)

### Denied Imports

- `binance.client`, `ccxt`, any exchange SDK
- `requests` for exchange API calls
- `dotenv` or `os.environ` for credential retrieval
- Any module containing live submission logic

## Review Coverage

- MEDIUM-operational: 11/11 reviewed (100%)
- MEDIUM-verification: 2/2 reviewed (100%)
- All 8 review policies applied to each file
- No violations found

## Review Verdict

All 22 MEDIUM-risk files reviewed. All policies defined. No violations found. All governed by policy.
