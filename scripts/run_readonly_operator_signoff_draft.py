"""Runner: read-only operator signoff draft."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_release_gate"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_release_gate"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_release_gate.operator_signoff_draft")
    draft = mod.create_draft()
    mod.write_draft(draft, OUT_DIR / "operator_signoff_draft.json")
    report = mod.render_report(draft)
    (REPORT_DIR / "operator_signoff_draft_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "operator_signoff_draft_report.md").write_text(report, encoding="utf-8")
    print(f"operator_signoff_draft: {len(draft.sections)} sections")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
