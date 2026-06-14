"""Runner: read-only release blocker ledger."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_release_gate"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_release_gate"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_release_gate.release_blocker_ledger")
    ledger = mod.create_ledger()
    mod.write_ledger(ledger, OUT_DIR / "release_blocker_ledger.json")
    report = mod.render_report(ledger)
    (REPORT_DIR / "release_blocker_ledger_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "release_blocker_ledger_report.md").write_text(report, encoding="utf-8")
    active = mod.count_active(ledger)
    print(f"release_blocker_ledger: {len(ledger.blockers)} blockers, {active} active")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
