"""Runner: read-only discovery dry-run packet."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_discovery"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_discovery"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_discovery.discovery_dry_run_packet")
    packet = mod.create_packet()
    mod.write_packet(packet, OUT_DIR / "discovery_dry_run_packet.json")
    report = mod.render_report(packet)
    (REPORT_DIR / "discovery_dry_run_packet_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "discovery_dry_run_packet_report.md").write_text(report, encoding="utf-8")
    print(f"discovery_dry_run_packet: {len(packet.blocker_summary)} blockers")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
