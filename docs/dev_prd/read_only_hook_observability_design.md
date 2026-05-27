# Read-Only Hook Observability Design

## Purpose

Define the observation points and logging contract for the read-only hook system. Observability must provide full visibility into hook behavior without leaking sensitive data.

## Contract

Every hook lifecycle event emits an observation event at a defined point. Observation events are structured, timestamped, and sanitized. No PII, secrets, or credentials appear in observability data.

## Fields / Items

| Observation Point | Description | Required Fields |
|-------------------|-------------|-----------------|
| `hook_invocation` | Hook was called | timestamp, hook_id, input_hash |
| `permission_check` | Permission validated | timestamp, hook_id, permission, result |
| `invariant_check` | Invariant verified | timestamp, hook_id, invariant_name, passed |
| `sanitization` | Output sanitized | timestamp, hook_id, fields_sanitized |
| `output_generation` | Output produced | timestamp, hook_id, output_hash |

## Rules

1. No PII in logs — names, emails, account IDs must be hashed or redacted.
2. No secrets in observability data — API keys, tokens, passwords must never appear.
3. Every observation point must emit an event — no silent failures.
4. Observation events must be append-only — no mutation after emission.
5. Observability must work in dry-run and production identically.

## Safety

- Observability is read-only — it cannot modify hook behavior.
- Log storage must be access-controlled.
- Observation data retention follows project data policy.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
