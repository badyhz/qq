#!/usr/bin/env python3
"""T74001 — No-Submit Runtime Regression."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.safety.no_submit_regression import run_safety_checks, write_checks

def main():
    checks = run_safety_checks(ROOT / "data", ROOT / "reports")
    write_checks(checks, ROOT / "data" / "runtime" / "safety" / "no_submit_regression.json")
    passed = sum(1 for c in checks if c.passed)
    print(f"Safety: {passed}/{len(checks)} checks passed")

if __name__ == "__main__":
    main()
