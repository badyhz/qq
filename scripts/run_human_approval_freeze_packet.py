"""Runner: human approval freeze packet."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "freeze_packet"
REPORT_DIR = ROOT / "reports" / "freeze_packet"

def main() -> int:
    packet_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.human_approval_freeze_packet")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.freeze_packet_validator")

    packet = packet_mod.create_freeze_packet()
    packet_mod.write_packet(packet, OUT_DIR / "freeze_packet.json")
    report = packet_mod.render_report(packet)
    (REPORT_DIR / "freeze_packet.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "freeze_packet.md").write_text(report, encoding="utf-8")

    checks = validator_mod.validate_freeze_packet(packet.to_dict())
    validator_mod.write_checks(checks, OUT_DIR / "freeze_packet_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"freeze_packet: {len(packet.frozen_gates)} frozen gates")
    print(f"freeze_packet_checks: {passed}/{len(checks)} passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
