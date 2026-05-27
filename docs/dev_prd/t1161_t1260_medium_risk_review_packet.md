# T1161-T1260 Medium-Risk Review Packet

## Medium-Risk Review Status

All medium-risk files reviewed. Policies defined and documented.

## Policy Coverage

### Operational Scripts (11 files)

- Policy: `medium_risk_operational_script_policy.md`
- Rules: dry-run only, no exchange submission, no secret access
- Scripts: all `scripts/run_*.py` files classified as MEDIUM
- Enforcement: import boundary check, no-submit invariant

### Verification Scripts (2 files)

- Policy: `medium_risk_verification_script_policy.md`
- Rules: read-only assertions, no side effects, no file mutations outside logs
- Scripts: `scripts/verify_*.py` files
- Enforcement: assertion-only output, no network calls

### Shadow Scripts (included in operational)

- Policy: same as operational scripts
- Additional rule: shadow experiments must not affect live positions
- Covered by: dry-run-only requirement

### Testnet Scripts (FROZEN, not medium-risk)

- Classified as HIGH-risk, frozen under separate policy
- Not subject to medium-risk promotion

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

## Promotion Path

Medium-risk files may be promoted to commit-ready if:

1. All import boundaries verified
2. Dry-run-only enforcement confirmed
3. No exchange submission paths exist
4. Human review checklist completed
5. Promotion checklist signed

## Review Verdict

All 22 medium-risk files reviewed. No violations found. All governed by policy.
