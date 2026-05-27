# Runtime Governance Schema Checker

## Overview

Pure structural schema checks for serialized runtime governance objects. No JSON schema dependency. Uses deterministic expected field lists for validation.

## API

### `check_runtime_input_dict_schema(data: Dict) -> RuntimeGovernanceSchemaCheck`

Validates a runtime input dict has exactly the expected fields.

**Expected fields:** `run_id`, `adapter_id`, `mode`, `requested_action`, `symbol`, `environment`, `allow_network`, `allow_submit`, `allow_file_io`, `metadata`

### `check_preflight_packet_dict_schema(data: Dict) -> RuntimeGovernanceSchemaCheck`

Validates a preflight packet dict has exactly the expected fields.

**Expected fields:** `input`, `dry_run_result`, `audit_event`, `final_verdict`, `proceed`, `notes`

### `schema_check_to_dict(check) -> Dict`

Serializes a `RuntimeGovernanceSchemaCheck` to a plain dict.

### `schema_check_to_markdown(check) -> str`

Serializes a `RuntimeGovernanceSchemaCheck` to deterministic markdown.

## RuntimeGovernanceSchemaCheck

```python
@dataclass(frozen=True)
class RuntimeGovernanceSchemaCheck:
    ok: bool
    object_type: str
    missing_fields: List[str]   # sorted
    unexpected_fields: List[str] # sorted
    notes: List[str]
```

## Determinism

- `missing_fields` and `unexpected_fields` are always sorted.
- `schema_check_to_dict` and `schema_check_to_markdown` produce identical output for identical input.
