# Read-Only Hook Input Contract

## Purpose

Define the input structure for all read-only hook invocations. Every call into a read-only hook MUST provide exactly these fields, no more, no less.

## Contract

```yaml
input:
  hook_id: string
  operation_kind: enum
  payload: object
  permission_envelope: object
  context: object
```

## Fields / Items

### hook_id
- Type: `string`
- Format: `roh-{domain}-{verb}` (e.g., `roh-market-read`, `roh-position-query`)
- Required: YES
- Unique per hook definition.

### operation_kind
- Type: `enum`
- Allowed values: `query`, `validate`, `inspect`, `audit`, `snapshot`
- Required: YES
- Determines which invariant set applies.

### payload
- Type: `object`
- Required: YES
- Contains the data the hook will analyze.
- MUST NOT contain secrets, credentials, API keys, or live account state.
- Keys MUST be declared in the hook's field manifest.

### permission_envelope
- Type: `object`
- Required: YES
- Fields:
  - `granted_flags`: list of read-only permission flags.
  - `source`: origin of the permission grant (e.g., `config`, `caller`, `frozen`).
  - `expiry`: optional expiry marker; `null` means no expiry.
- If `source` is `FROZEN`, all write flags are stripped regardless of `granted_flags`.

### context
- Type: `object`
- Required: YES
- Fields:
  - `caller_id`: string identifying the calling module.
  - `timestamp`: externally provided timestamp; hook MUST NOT generate its own.
  - `dry_run`: boolean, defaults to `true`.

## Rules

1. No secrets in payload. Payload is sanitized BEFORE input construction; see `read_only_hook_sanitized_payload_design.md`.
2. No mutable state references. Payload MUST contain copies, not pointers or references to live objects.
3. All fields are required. Missing field = `PERMISSION_DENIED` or `INVARIANT_VIOLATION`, never a default fill.
4. `hook_id` MUST match a registered hook definition; unregistered ID = immediate rejection.
5. `permission_envelope` is the single source of truth for what the hook MAY do.

## Safety

- Input construction is a pure function: same inputs produce same input object.
- No I/O during input construction.
- No auto-population of fields from runtime state.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
