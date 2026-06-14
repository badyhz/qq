"""Runner: replay-to-governance trace validator."""
from __future__ import annotations
import importlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_replay"
REPORT_DIR = ROOT / "reports" / "testnet_mock_replay"

def main() -> int:
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.replay_governance_trace_validator")
    harness_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.mock_replay_harness")
    scenario_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.replay_scenario_matrix")
    bundle_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.mock_field_test_evidence_bundle")
    packet_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.human_approval_packet_v3")

    # Build traces
    scenarios = scenario_mod.get_scenarios()
    traces = []
    for s in scenarios:
        trace = harness_mod.run_replay(
            s.scenario_id, s.method, s.path, s.body,
            s.fixture_name, s.status_code, s.response_body, s.expected_decision
        )
        traces.append(trace.to_dict())

    # Validate traces
    trace_checks = validator_mod.validate_traces(traces)

    # Validate evidence bundle
    bundle = bundle_mod.create_bundle(len(scenarios), len(scenarios), 0)
    bundle_checks = validator_mod.validate_evidence_bundle(bundle.to_dict())

    # Validate approval packet
    packet = packet_mod.create_packet(bundle.bundle_id)
    packet_checks = validator_mod.validate_approval_packet(packet.to_dict())

    all_checks = trace_checks + bundle_checks + packet_checks
    validator_mod.write_checks(all_checks, OUT_DIR / "trace_validator_checks.json")
    report = validator_mod.render_report(all_checks)
    (REPORT_DIR / "replay_governance_trace_validator.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "replay_governance_trace_validator.md").write_text(report, encoding="utf-8")

    passed = sum(1 for c in all_checks if c.passed)
    print(f"trace_validator: {passed}/{len(all_checks)} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
