"""Runner: discovery governance checklist."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_discovery"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_discovery"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_discovery.discovery_governance_checklist")
    checklist = mod.create_checklist()
    mod.write_checklist(checklist, OUT_DIR / "discovery_governance_checklist.json")
    report = mod.render_report(checklist)
    (REPORT_DIR / "discovery_governance_checklist_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "discovery_governance_checklist_report.md").write_text(report, encoding="utf-8")
    print(f"discovery_governance_checklist: {len(checklist.items)} items")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
