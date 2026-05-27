# Runtime Governance Dry-Run Matrix Report

Runs all sample factory kinds through the preflight pipeline and summarizes verdicts.

## Module

`core/runtime_governance_dry_run_matrix_report.py`

## Dataclass

```python
@dataclass(frozen=True)
class RuntimeGovernanceDryRunMatrixRow:
    kind: str
    final_verdict: str
    ready_for_runtime: bool
    blocker_count: int
    ok: bool
```

## Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `build_runtime_governance_dry_run_matrix_report()` | `List[RuntimeGovernanceDryRunMatrixRow]` | Run all 5 sample kinds through preflight |
| `dry_run_matrix_to_dict(matrix)` | `List[Dict]` | Serialize to list of dicts |
| `dry_run_matrix_to_markdown(matrix)` | `str` | Render as markdown table |

## Sample Kinds

| Kind | Expected Verdict | Ready |
|------|-----------------|-------|
| `pass` | PASS | yes |
| `fail` | FAIL | no |
| `blocked` | BLOCKED | no |
| `warn_like` | WARN | no |
| `invalid_contract` | FAIL | no |

## Dependencies

- `core.runtime_governance_sample_factory` — `build_runtime_governance_sample_preflight_packet`
- `core.runtime_governance_preflight_packet` — `RuntimeGovernancePreflightPacket`

## Tests

`tests/unit/test_runtime_governance_dry_run_matrix_report.py`

- Includes all 5 kinds
- `pass` → `ready_for_runtime=True`
- `blocked` → `ready_for_runtime=False`, `blocker_count > 0`
- Dict output deterministic
- Markdown output deterministic
