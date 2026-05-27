# T832 — Read-Only Invariant Checker

Module: `core.runtime_governance_readonly_invariant_checker.py`

Pure, deterministic checker that validates a `RuntimeGovernancePermissionEnvelope`
conforms to read-only constraints. No I/O, no timestamps, no network.

## Invariants

| ID | Check | Severity on fail |
|---|---|---|
| `no_write` | `allow_write == False` | error |
| `no_network` | `allow_network == False` | error |
| `no_order` | `allow_order == False` | error |
| `no_account_mutation` | `allow_account_mutation == False` | error |
| `no_secret_access` | `allow_secret_access == False` | error |
| `read_allowed` | `allow_read == True` | error |

## API

```python
check_readonly_permission_invariants(envelope) -> List[RuntimeGovernanceReadOnlyInvariant]
summarize_readonly_invariants(results) -> Dict[str, Any]
readonly_invariants_to_dict(results) -> List[Dict[str, Any]]
readonly_invariants_to_markdown(results) -> str
```

## Usage

```python
from core.runtime_governance_permission_envelope import build_runtime_governance_permission_envelope
from core.runtime_governance_readonly_invariant_checker import (
    check_readonly_permission_invariants,
    summarize_readonly_invariants,
)

envelope = build_runtime_governance_permission_envelope("readonly_safe")
results = check_readonly_permission_invariants(envelope)
summary = summarize_readonly_invariants(results)
assert summary["all_ok"]
```

## Tests

```
python3 -m pytest tests/unit/test_runtime_governance_readonly_invariant_checker.py -v
```
