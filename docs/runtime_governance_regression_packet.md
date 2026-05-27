# Runtime Governance Regression Packet

Combines scenario evaluations, invariant summaries, and manifest into one
deterministic regression packet.

## Purpose

Single entry point for runtime governance regression testing. Evaluates the
full scenario catalog, runs invariant checks across all scenarios, and
inspects the stack manifest — then resolves a final verdict.

## Verdict Logic

| Condition | Verdict |
|---|---|
| All scenarios ok AND manifest PASS | PASS |
| All scenarios ok AND manifest WARN | WARN |
| Any scenario not ok OR manifest FAIL | FAIL |

## API

### Dataclass

```python
@dataclass(frozen=True)
class RuntimeGovernanceRegressionPacket:
    title: str
    scenario_count: int
    scenario_pass_count: int
    scenario_fail_count: int
    invariant_summary: Dict[str, Any]
    manifest_summary: Dict[str, Any]
    final_verdict: str  # PASS / WARN / FAIL
    notes: List[str]
```

### Functions

- `build_runtime_governance_regression_packet(*, title="Runtime Governance Regression", notes=None) -> RuntimeGovernanceRegressionPacket`
- `runtime_regression_packet_to_dict(packet) -> Dict`
- `runtime_regression_packet_to_markdown(packet) -> str`

## Dependencies

- `core.runtime_governance_scenario_batch_evaluator` — scenario evaluation
- `core.runtime_governance_invariant_checker` — invariant checks
- `core.runtime_governance_stack_manifest` — manifest build/summary
- `core.runtime_governance_scenario_catalog` — scenario catalog

## Properties

- Pure. No I/O. No network. No random. No timestamps.
- Deterministic: same inputs produce same outputs.
- Frozen dataclass: immutable after construction.
