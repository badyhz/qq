# T835: Runtime Governance Read-Only Regression Packet

## Purpose

Combines read-only scenario evaluations, side-effect declarations, and manifest into a single frozen dataclass with deterministic verdict logic.

## Module

`core/runtime_governance_readonly_regression_packet.py`

## Dataclass

`RuntimeGovernanceReadOnlyRegressionPacket` (frozen=True)

Fields: title, scenario_count, scenario_pass_count, scenario_fail_count, side_effect_verdict, manifest_verdict, final_verdict, notes.

## Verdict Logic

- PASS: scenario_fail_count==0 AND side_effect_verdict=="PASS" AND manifest_verdict=="PASS"
- FAIL: otherwise

## Functions

- `build_readonly_regression_packet(...)` - construct packet with defaults (all PASS, 6 scenarios)
- `readonly_regression_packet_to_dict(packet)` - serialize to dict
- `readonly_regression_packet_to_markdown(packet)` - render as markdown table

## Constraints

Pure, deterministic, no I/O, no timestamps, no random.
