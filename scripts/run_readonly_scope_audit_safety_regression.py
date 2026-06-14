"""Runner: readonly scope audit safety regression."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_scope_audit"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_scope_audit"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_scope_audit.scope_audit_safety_regression")
    items = mod.run_regression()
    mod.write_regression(items, OUT_DIR / "scope_audit_safety_regression.json")
    report = mod.render_report(items)
    (REPORT_DIR / "scope_audit_safety_regression_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "scope_audit_safety_regression_report.md").write_text(report, encoding="utf-8")
    passed = sum(1 for i in items if i.passed)
    print(f"safety_regression: {passed}/{len(items)} passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
