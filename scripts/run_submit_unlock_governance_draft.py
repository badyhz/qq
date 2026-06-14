"""Runner: submit unlock governance draft."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

def main() -> int:
    gov_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.submit_unlock_governance")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.submit_unlock_governance_validator")

    items = gov_mod.get_items()
    gov_mod.write_governance(items, OUT_DIR / "submit_unlock_governance.json")
    report = gov_mod.render_report(items)
    (REPORT_DIR / "submit_unlock_governance_draft.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "submit_unlock_governance_draft.md").write_text(report, encoding="utf-8")

    checks = validator_mod.validate_governance(report)
    validator_mod.write_checks(checks, OUT_DIR / "submit_unlock_governance_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"submit_unlock_governance: {len(items)} items, {passed}/{len(checks)} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
