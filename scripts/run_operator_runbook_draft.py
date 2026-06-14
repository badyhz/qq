"""Runner: operator runbook draft."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

def main() -> int:
    runbook_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.operator_runbook")

    steps = runbook_mod.get_steps()
    runbook_mod.write_runbook(steps, OUT_DIR / "operator_runbook.json")
    report = runbook_mod.render_report(steps)
    (REPORT_DIR / "operator_runbook_draft.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "operator_runbook_draft.md").write_text(report, encoding="utf-8")

    print(f"operator_runbook: {len(steps)} steps")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
