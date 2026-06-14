"""Runner: read-only discovery release gate."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_release_gate"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_release_gate"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_release_gate.release_gate")
    packet = mod.create_packet()
    mod.write_packet(packet, OUT_DIR / "release_gate_packet.json")
    report = mod.render_report(packet)
    (REPORT_DIR / "release_gate_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "release_gate_report.md").write_text(report, encoding="utf-8")
    print(f"release_gate: {len(packet.criteria)} criteria")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
