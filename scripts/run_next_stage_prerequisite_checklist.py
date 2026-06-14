"""Runner: next-stage prerequisite checklist."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_closeout"
REPORT_DIR = ROOT / "reports" / "testnet_mock_closeout"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_mock_closeout.next_stage_prerequisite_checklist")
    checklist = mod.create_checklist()
    mod.write_checklist(checklist, OUT_DIR / "next_stage_prerequisite_checklist.json")
    report = mod.render_report(checklist)
    (REPORT_DIR / "next_stage_prerequisite_checklist_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "next_stage_prerequisite_checklist_report.md").write_text(report, encoding="utf-8")
    print(f"next_stage_prerequisite_checklist: {len(checklist.items)} items, next_stage={checklist.next_stage}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
