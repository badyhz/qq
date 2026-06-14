"""Runner: operator_handoff_packet."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_final_governance_freeze"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_final_governance_freeze"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_final_governance_freeze.operator_handoff_packet")
    obj = mod.create_packet()
    mod.write_packet(obj, OUT_DIR / "operator_handoff_packet.json")
    report = mod.render_report(obj)
    (REPORT_DIR / "operator_handoff_packet_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "operator_handoff_packet_report.md").write_text(report, encoding="utf-8")
    print(f"operator_handoff_packet: created")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
