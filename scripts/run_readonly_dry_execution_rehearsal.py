"""Runner: dry_execution_rehearsal."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_dry_execution_rehearsal"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_dry_execution_rehearsal"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.dry_execution_rehearsal")
    obj = mod.create_rehearsal()
    mod.write_rehearsal(obj, OUT_DIR / "dry_execution_rehearsal.json")
    report = mod.render_report(obj)
    (REPORT_DIR / "dry_execution_rehearsal_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "dry_execution_rehearsal_report.md").write_text(report, encoding="utf-8")
    print(f"dry_execution_rehearsal: created")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
