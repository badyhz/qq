# Read-Only Hook Sanitized Payload Design

## Purpose

Define how the payload is sanitized before it enters the read-only hook. The sanitizer removes secrets, credentials, API keys, and account state to ensure the hook never processes sensitive data.

## Contract

```yaml
sanitizer:
  input: raw_payload (object)
  output: sanitized_payload (object)
  behavior: deterministic redaction
```

## Fields / Items

### Input
- Any object intended as the hook's `payload` field.

### Output
- Same structure as input, with sensitive fields replaced by `"[REDACTED]"`.
- Non-sensitive fields pass through unchanged.

### Sanitized Field Patterns

Fields matching ANY of these patterns are redacted:

| Pattern | Example Match |
|---|---|
| `*api_key*` | `api_key`, `binance_api_key`, `apiKey` |
| `*secret*` | `secret`, `api_secret`, `clientSecret` |
| `*credential*` | `credential`, `credentials`, `credential_store` |
| `*password*` | `password`, `passphrase`, `pwd` |
| `*token*` | `token`, `access_token`, `refresh_token`, `auth_token` |
| `*private_key*` | `private_key`, `privateKey`, `priv_key` |
| `*account_balance*` | `account_balance`, `balance`, `available_balance` |
| `*position*` | `position`, `positions`, `open_position` |
| `*order*` | `order_id`, `client_order_id`, `open_orders` |
| `*wallet*` | `wallet`, `wallet_address`, `wallet_balance` |

### Redaction Rules
- Case-insensitive matching.
- Nested objects: patterns applied recursively.
- Arrays: patterns applied to each element's keys.
- Values replaced with literal string `"[REDACTED]"`.

## Rules

1. Redaction must be deterministic. Same input always produces same output.
2. Field patterns are the single source of truth. New patterns require design doc update.
3. Sanitizer runs BEFORE hook invocation. Hook never sees raw payload.
4. Sanitizer is a pure function: no I/O, no side effects.
5. If a field matches multiple patterns, it is redacted once (not double-redacted).

## Safety

- Sanitizer has no access to secrets store, environment, or runtime state.
- Sanitizer does not log raw values.
- Sanitizer output is included in evidence record for audit.
- If sanitizer encounters an unrecognizable structure, it redacts the entire object and flags `SANITIZATION_FAILURE`.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
