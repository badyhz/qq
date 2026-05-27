# T842: Runtime Governance Read-Only Manual Review Packet

## Purpose

Define exact human review packet for future read-only hook implementation.

## Design

- Pure, deterministic, no I/O, no timestamps, no random.
- Frozen dataclass prevents mutation after construction.
- Three pure functions: build, to_dict, to_markdown.

## API

### Dataclass

```python
@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyManualReviewPacket:
    allowed_review_items: List[str]
    forbidden_actions: List[str]
    required_evidence: List[str]
    decision_options: List[str]
    notes: List[str]
```

### Functions

| Function | Input | Output |
|---|---|---|
| `build_readonly_manual_review_packet()` | none | `RuntimeGovernanceReadOnlyManualReviewPacket` |
| `readonly_manual_review_packet_to_dict(packet)` | packet | `Dict` |
| `readonly_manual_review_packet_to_markdown(packet)` | packet | `str` |

## Defaults

### Allowed Review Items (10)

read-only hook spec, permission envelope, invariant checker, side-effect declarations, scenario catalog, regression packet, readiness score, blocker summary, evidence packet, transition checklist

### Forbidden Actions (7)

live trading, order placement, secret access, exchange connection, planner autonomous mode, file write, network call

### Required Evidence (9)

permission envelope PASS, invariant checker PASS, side-effect declaration PASS, scenario catalog PASS, regression packet PASS, readiness score >= B, blocker summary PROCEED, evidence packet PASS, transition checklist complete

### Decision Options (2)

APPROVE_READONLY_DESIGN_ONLY, REQUEST_CHANGES

### Notes (3)

- Approval is for read-only design only.
- Does not authorize live trading.
- Does not authorize order placement.
