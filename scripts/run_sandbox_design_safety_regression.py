#!/usr/bin/env python3
"""Wave 9: Sandbox design safety regression."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.sandbox_design_safety_regression import run_safety_regression, write_checks, render_safety_report

    checks = run_safety_regression(ROOT)
    write_checks(checks, ROOT / "data" / "runtime" / "testnet_sandbox" / "sandbox_design_safety_regression.json")
    (ROOT / "reports" / "sandbox_design_safety_regression_report.md").write_text(render_safety_report(checks), encoding="utf-8")

    ok = all(c.passed for c in checks)
    print(f"Sandbox design safety: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
