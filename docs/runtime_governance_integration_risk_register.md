# Runtime Governance Integration Risk Register

Pure risk catalog for runtime governance integration. No I/O. No network. No live system dependency.

## Module

`core/runtime_governance_integration_risk_register.py`

## Dataclass

```python
@dataclass(frozen=True)
class RuntimeGovernanceIntegrationRisk:
    risk_id: str
    title: str
    severity: str     # "low","medium","high","critical"
    likelihood: str   # "low","medium","high"
    mitigation: str
    status: str       # "open","mitigated","accepted"
```

## Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `build_runtime_governance_integration_risk_register` | `() -> List[RuntimeGovernanceIntegrationRisk]` | Build the 8-item risk register |
| `risk_register_to_dict` | `(register) -> List[Dict]` | Serialize to plain dicts |
| `risk_register_to_markdown` | `(register) -> str` | Render as markdown table + detail sections |
| `summarize_risk_register` | `(register) -> Dict[str, Any]` | Counts by severity, likelihood, status |

## Risks

| Risk ID | Severity | Likelihood |
|---------|----------|------------|
| accidental_submit | critical | high |
| network_permission_leak | high | high |
| stale_governance_verdict | medium | medium |
| missing_manual_approval | high | high |
| planner_bypass | critical | high |
| secret_exposure | critical | medium |
| untracked_file_io | medium | medium |
| nondeterministic_evidence | low | medium |

All risks start with status="open" and non-empty mitigation strings.

## Tests

`tests/unit/test_runtime_governance_integration_risk_register.py`

Covers: count, uniqueness, frozen dataclass, valid enums, serialization round-trip, markdown output, summary aggregation, edge cases (empty register).
