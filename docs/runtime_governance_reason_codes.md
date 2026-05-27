# Runtime Governance Reason Codes

Stable reason code registry for runtime governance outcomes.

## Overview

Each `RuntimeGovernanceReasonCode` is a frozen dataclass with:
- `code` — unique identifier (e.g. `RG_OK`)
- `category` — `FailureCategory` enum value
- `severity` — `FailureSeverity` enum value
- `retryable` — whether the failure is retryable
- `description` — human-readable description

All functions are pure. No I/O. Deterministic output.

## API

### `build_runtime_governance_reason_code_registry() -> List[RuntimeGovernanceReasonCode]`

Returns a copy of the full 8-code registry.

### `get_runtime_governance_reason_code(code: str) -> RuntimeGovernanceReasonCode`

Looks up a reason code by its code string. Raises `ValueError` if not found.

### `reason_code_registry_to_dict(registry) -> List[Dict]`

Serializes registry to list of plain dicts with keys: `code`, `category`, `severity`, `retryable`, `description`.

### `reason_code_registry_to_markdown(registry) -> str`

Renders registry as a Markdown table.

## Code Table

| Code | Category | Severity | Retryable | Description |
|------|----------|----------|-----------|-------------|
| RG_OK | validation_failure | info | no | governance check passed |
| RG_MISSING_RUN_ID | validation_failure | error | no | missing run_id |
| RG_MISSING_ADAPTER_ID | validation_failure | error | no | missing adapter_id |
| RG_UNKNOWN_MODE | validation_failure | error | no | unknown governance mode |
| RG_SUBMIT_BLOCKED_NON_TEST | policy_block | critical | no | submit blocked outside test |
| RG_NETWORK_BLOCKED_MODE | policy_block | critical | no | network blocked without mode |
| RG_POLICY_BLOCK | policy_block | critical | no | general policy block |
| RG_UNKNOWN_FAILURE | unknown | error | yes | unknown governance failure |

## Determinism

- `reason_code_registry_to_dict` returns identical output for identical input across calls.
- `reason_code_registry_to_markdown` returns identical Markdown for identical input across calls.
- Registry order is fixed at module load time.
