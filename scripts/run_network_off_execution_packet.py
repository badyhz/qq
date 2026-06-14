"""Runner: network-off execution packet."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_release_gate"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_release_gate"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_release_gate.network_off_execution_packet")
    packet = mod.create_packet()
    mod.write_packet(packet, OUT_DIR / "network_off_execution_packet.json")
    report = mod.render_report(packet)
    (REPORT_DIR / "network_off_execution_packet_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "network_off_execution_packet_report.md").write_text(report, encoding="utf-8")
    print(f"network_off_execution_packet: {len(packet.steps)} steps")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
