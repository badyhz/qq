"""Runner: credential handling SOP."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_preapproval"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_preapproval"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_preapproval.credential_handling_sop")
    sop = mod.create_sop()
    mod.write_sop(sop, OUT_DIR / "credential_handling_sop.json")
    report = mod.render_report(sop)
    (REPORT_DIR / "credential_handling_sop_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "credential_handling_sop_report.md").write_text(report, encoding="utf-8")
    print(f"credential_handling_sop: {len(sop.sections)} sections")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
