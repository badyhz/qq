"""Runner: human approval packet v3."""
from __future__ import annotations
import importlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_replay"
REPORT_DIR = ROOT / "reports" / "testnet_mock_replay"

def main() -> int:
    packet_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.human_approval_packet_v3")
    bundle_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.mock_field_test_evidence_bundle")
    scenario_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.replay_scenario_matrix")

    scenarios = scenario_mod.get_scenarios()
    bundle = bundle_mod.create_bundle(len(scenarios), len(scenarios), 0)
    packet = packet_mod.create_packet(bundle.bundle_id)
    packet_mod.write_packet(packet, OUT_DIR / "human_approval_packet_v3.json")
    report = packet_mod.render_report(packet)
    (REPORT_DIR / "human_approval_packet_v3.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "human_approval_packet_v3.md").write_text(report, encoding="utf-8")

    print(f"human_approval_packet_v3: {packet.packet_id}, decision={packet.decision}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
