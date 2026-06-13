# Pre-commit Hook Configuration

- **Hook name:** qq-hygiene-check
- **Enabled:** True
- **Blocking:** True
- **Description:** Pre-commit hook to detect forbidden trading terms and security violations

## Checks

### forbidden_terms
- **Description:** Detect forbidden trading permission terms outside deny-list contexts
- **Severity:** BLOCK
- **Pattern:** `REAL_SUBMIT_ALLOWED|TESTNET_SUBMIT_ALLOWED|LIVE_TRADING|AUTO_SUBMIT_ENABLED`
- **Pre-commit compatible:** True

### hardcoded_secrets
- **Description:** Detect potential hardcoded API keys or secrets
- **Severity:** BLOCK
- **Pattern:** `(api_key|api_secret|password)\s*=\s*['\"][^'\"]+['\"]`
- **Pre-commit compatible:** True

### real_order_calls
- **Description:** Detect real order submission calls outside dry-run context
- **Severity:** WARN
- **Pattern:** `(create_order|submit_order|place_order)`
- **Pre-commit compatible:** True

### live_mode_flag
- **Description:** Detect enable_live_trading=True outside guard context
- **Severity:** BLOCK
- **Pattern:** `enable_live_trading\s*=\s*True`
- **Pre-commit compatible:** True
