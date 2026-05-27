# T855: Runtime Governance Read-Only Release Hold Packet

## Purpose

Explicitly hold any real runtime release until manual approval.

## Design

- Frozen dataclass: `RuntimeGovernanceReadOnlyReleaseHoldPacket`
- Pure, deterministic, no I/O, no timestamps, no random
- Default verdict: `HOLD`

## Fields

| Field | Type | Default |
|---|---|---|
| hold_active | bool | True |
| hold_reasons | List[str] | 4 defaults |
| allowed_actions | List[str] | review-only actions |
| forbidden_actions | List[str] | 6 forbidden actions |
| release_conditions | List[str] | 5 conditions |
| final_verdict | str | HOLD |

## Functions

- `build_readonly_release_hold_packet()` - construct default packet
- `readonly_release_hold_packet_to_dict(packet)` - serialize to dict
- `readonly_release_hold_packet_to_markdown(packet)` - serialize to markdown

## Files

- `core/runtime_governance_readonly_release_hold_packet.py`
- `tests/unit/test_runtime_governance_readonly_release_hold_packet.py`
