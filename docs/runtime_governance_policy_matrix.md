# Runtime Governance Policy Matrix

## Overview

Pure policy matrix for mode/environment/allow flags. No side effects, no I/O, deterministic.

Module: `core/runtime_governance_policy_matrix.py`

## API

```python
from core.runtime_governance_policy_matrix import (
    RuntimeGovernancePolicyCase,
    build_runtime_governance_policy_matrix,
    evaluate_runtime_governance_policy_case,
    policy_matrix_to_dict,
    policy_matrix_to_markdown,
)
```

- `build_runtime_governance_policy_matrix()` — returns `List[RuntimeGovernancePolicyCase]` (16 entries)
- `evaluate_runtime_governance_policy_case(mode, env, net, sub, file_io)` — returns `(bool, str)`
- `policy_matrix_to_dict(matrix)` — list of dicts
- `policy_matrix_to_markdown(matrix)` — markdown table string

## Policy Rules

| Rule | Description |
|------|-------------|
| prod env | Submit always blocked regardless of mode |
| local env | Submit blocked for all modes |
| shadow | No submit ever. No network unless mode set. File_io false by default |
| dry_run | No submit ever. No network unless mode set |
| testnet_dry | No submit. Network ok in test/testnet |
| testnet_submit_simulated | Submit allowed only in test/testnet |

## Modes

`shadow`, `dry_run`, `testnet_dry`, `testnet_submit_simulated`

## Environments

`local`, `test`, `testnet`, `prod`

## Determinism

All functions are pure. Repeated calls with identical inputs produce identical outputs.
