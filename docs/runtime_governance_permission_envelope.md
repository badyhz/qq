# T828 — Runtime Governance Permission Envelope

## Purpose

Encapsulate runtime permission decisions as a frozen dataclass. Each envelope declares which capabilities are allowed and a verdict (PASS / BLOCKED).

## Kinds

| Kind | read | write | network | order | account_mutation | secret_access | verdict |
|---|---|---|---|---|---|---|---|
| readonly_safe | T | F | F | F | F | F | PASS |
| write_blocked | T | T | F | F | F | F | BLOCKED |
| network_blocked | T | F | T | F | F | F | BLOCKED |
| order_blocked | T | F | F | T | F | F | BLOCKED |
| secret_blocked | T | F | F | F | F | T | BLOCKED |

## Verdict Rule

PASS only when `allow_read=True` AND all dangerous flags (`write`, `network`, `order`, `account_mutation`, `secret_access`) are False.

## API

```python
build_runtime_governance_permission_envelope(kind: str) -> RuntimeGovernancePermissionEnvelope
evaluate_permission_envelope(envelope) -> str
permission_envelope_to_dict(envelope) -> Dict[str, Any]
permission_envelope_to_markdown(envelope) -> str
```

## Usage

```python
from core.runtime_governance_permission_envelope import (
    build_runtime_governance_permission_envelope,
    evaluate_permission_envelope,
)

env = build_runtime_governance_permission_envelope("readonly_safe")
assert evaluate_permission_envelope(env) == "PASS"
```
