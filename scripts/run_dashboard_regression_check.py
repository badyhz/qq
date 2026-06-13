#!/usr/bin/env python3
"""T71001 — Dashboard Regression Check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.operator.dashboard_regression import check_dashboard, write_regression

def main():
    state_path = ROOT / "data" / "runtime" / "operator" / "system_state.json"
    dash_path = ROOT / "reports" / "operator_dashboard.html"
    checks = check_dashboard(state_path, dash_path)
    write_regression(checks, ROOT / "data" / "runtime" / "operator" / "dashboard_regression.json")
    passed = sum(1 for c in checks if c.passed)
    print(f"Dashboard regression: {passed}/{len(checks)} passed")

if __name__ == "__main__":
    main()
