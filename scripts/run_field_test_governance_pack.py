"""Runner: field-test governance pack."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

def main() -> int:
    gov_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.field_test_governance_pack")

    checklists = gov_mod.get_checklists()
    gov_mod.write_governance(checklists, OUT_DIR / "field_test_governance_pack.json")
    report = gov_mod.render_report(checklists)
    (REPORT_DIR / "field_test_governance_pack.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "field_test_governance_pack.md").write_text(report, encoding="utf-8")

    print(f"field_test_governance_pack: {len(checklists)} checklist items")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
