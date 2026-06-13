#!/usr/bin/env python3
"""Wave 9: Final gate safety regression."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_final_gate.final_gate_safety_regression import run_regression, write_checks, render_report
    checks = run_regression(ROOT)
    write_checks(checks, ROOT / "data" / "runtime" / "testnet_final_gate" / "final_gate_safety_regression.json")
    (ROOT / "reports" / "final_gate_safety_regression_report.md").write_text(render_report(checks), encoding="utf-8")
    ok = all(c.passed for c in checks)
    print(f"Final gate safety: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
