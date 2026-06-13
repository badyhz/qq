"""Runner: enablement no-submit safety regression."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "enablement_safety"
REPORT_DIR = ROOT / "reports" / "enablement_safety"

def main() -> int:
    regression_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.enablement_safety_regression")

    items = regression_mod.run_regression()
    regression_mod.write_regression(items, OUT_DIR / "enablement_safety_regression.json")
    report = regression_mod.render_report(items)
    (REPORT_DIR / "enablement_safety_regression.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "enablement_safety_regression.md").write_text(report, encoding="utf-8")

    passed = sum(1 for i in items if i.passed)
    failed = sum(1 for i in items if not i.passed)
    print(f"enablement_safety_regression: {passed}/{len(items)} passed, {failed} failed")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
