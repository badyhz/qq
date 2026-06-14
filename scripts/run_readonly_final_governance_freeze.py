"""Runner: final_governance_freeze."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_final_governance_freeze"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_final_governance_freeze"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_final_governance_freeze.final_governance_freeze")
    obj = mod.create_freeze()
    mod.write_freeze(obj, OUT_DIR / "final_governance_freeze.json")
    report = mod.render_report(obj)
    (REPORT_DIR / "final_governance_freeze_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "final_governance_freeze_report.md").write_text(report, encoding="utf-8")
    print(f"final_governance_freeze: created")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
