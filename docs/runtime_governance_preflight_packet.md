# Runtime Governance Preflight Packet

Combines contract validation, dry-run evaluation, and audit event into a single immutable preflight packet for runtime governance decisions.

## Data Model

**`RuntimeGovernancePreflightPacket`** (frozen dataclass):
- `input` — the original `RuntimeGovernanceInput`
- `dry_run_result` — full `RuntimeGovernanceDryRunResult` (contract, report, regression packet)
- `audit_event` — `RuntimeGovernanceAuditEvent` with deterministic event_id
- `final_verdict` — `"PASS"`, `"FAIL"`, or `"BLOCKED"`
- `proceed` — `True` only if `final_verdict == "PASS"`
- `notes` — collected notes from caller

## Usage

```python
from core.runtime_governance_contract import RuntimeGovernanceInput
from core.runtime_governance_preflight_packet import (
    build_runtime_governance_preflight_packet,
    preflight_packet_to_dict,
    preflight_packet_to_markdown,
)

inp = RuntimeGovernanceInput(
    run_id="run-001",
    adapter_id="adapter-001",
    mode="dry_run",
    requested_action="scan",
    symbol="BTCUSDT",
    environment="test",
    allow_network=False,
    allow_submit=False,
    allow_file_io=False,
)

pkt = build_runtime_governance_preflight_packet(inp)
assert pkt.proceed is True
assert pkt.final_verdict == "PASS"

# serialize
d = preflight_packet_to_dict(pkt)
md = preflight_packet_to_markdown(pkt)
```

## Design

- Pure. No I/O. No network. No random. No timestamps.
- Deterministic output for same inputs.
- Frozen dataclass — immutable after construction.
- Delegates to existing contract, dry-run adapter, and audit event modules.
