# Repo Hygiene Report

## Forbidden Terms Policy

The following terms are forbidden outside deny-list contexts:

- `REAL_SUBMIT_ALLOWED`
- `TESTNET_SUBMIT_ALLOWED`
- `LIVE_TRADING`
- `AUTO_SUBMIT_ENABLED`

## Allowed Contexts

Forbidden terms may appear in:
- `FORBIDDEN_`
- `denylist`
- `deny_list`
- `deny-list`
- `forbidden`

## Pre-commit Hook Checks

- **forbidden_terms** [BLOCK]: Detect forbidden trading permission terms outside deny-list contexts
- **hardcoded_secrets** [BLOCK]: Detect potential hardcoded API keys or secrets
- **real_order_calls** [WARN]: Detect real order submission calls outside dry-run context
- **live_mode_flag** [BLOCK]: Detect enable_live_trading=True outside guard context

## Recommended .pre-commit-config.yaml

```yaml
repos:
  - repo: local
    hooks:
      - id: qq-hygiene-check
        name: QQ Hygiene Check
        entry: python scripts/check_repo_hygiene.py
        language: system
        always_run: true
        pass_filenames: false
```
