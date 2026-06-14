"""Runner: read-only discovery operator checklist."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_preapproval"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_preapproval"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_preapproval.operator_checklist")
    checklist = mod.create_checklist()
    mod.write_checklist(checklist, OUT_DIR / "operator_checklist.json")
    report = mod.render_report(checklist)
    (REPORT_DIR / "operator_checklist_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "operator_checklist_report.md").write_text(report, encoding="utf-8")
    print(f"operator_checklist: {len(checklist.items)} items")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
