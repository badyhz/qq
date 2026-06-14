"""Runner: field-test acceptance criteria."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

def main() -> int:
    criteria_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.field_test_acceptance_criteria")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.field_test_validator")

    criteria = criteria_mod.get_criteria()
    criteria_mod.write_criteria(criteria, OUT_DIR / "field_test_acceptance_criteria.json")
    report = criteria_mod.render_report(criteria)
    (REPORT_DIR / "field_test_acceptance_criteria.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "field_test_acceptance_criteria.md").write_text(report, encoding="utf-8")

    checks = validator_mod.validate_criteria(report)
    validator_mod.write_checks(checks, OUT_DIR / "field_test_acceptance_criteria_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"field_test_acceptance_criteria: {len(criteria)} criteria, {passed}/{len(checks)} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
