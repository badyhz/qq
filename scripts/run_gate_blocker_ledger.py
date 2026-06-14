"""Runner: gate blocker ledger."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_closeout"
REPORT_DIR = ROOT / "reports" / "testnet_mock_closeout"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_mock_closeout.gate_blocker_ledger")
    ledger = mod.create_ledger()
    mod.write_ledger(ledger, OUT_DIR / "gate_blocker_ledger.json")
    report = mod.render_report(ledger)
    (REPORT_DIR / "gate_blocker_ledger_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "gate_blocker_ledger_report.md").write_text(report, encoding="utf-8")
    by_sev = mod.count_by_severity(ledger)
    print(f"gate_blocker_ledger: {len(ledger.blockers)} blockers, {by_sev}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
