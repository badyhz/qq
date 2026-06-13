"""Runner: external sandbox adapter plan."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "adapter_plan"
REPORT_DIR = ROOT / "reports" / "adapter_plan"

def main() -> int:
    plan_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.external_adapter_plan")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.external_adapter_plan_validator")

    sections = plan_mod.get_sections()
    plan_mod.write_plan(sections, OUT_DIR / "adapter_plan.json")
    report = plan_mod.render_plan_report(sections)
    (REPORT_DIR / "adapter_plan.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "adapter_plan.md").write_text(report, encoding="utf-8")

    plan_content = report
    checks = validator_mod.validate_plan(plan_content)
    validator_mod.write_checks(checks, OUT_DIR / "adapter_plan_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"adapter_plan: {len(sections)} sections")
    print(f"adapter_plan_checks: {passed}/{len(checks)} passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
