"""Paper ops suite runner — executes all ops modules."""
from __future__ import annotations
import importlib, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
ROOT = pathlib.Path(__file__).resolve().parent.parent

MODULES = [
    "run_paper_ops_log_freshness",
    "run_paper_ops_state_audit",
    "run_paper_ops_strategy_metrics",
    "run_paper_ops_signal_dashboard",
    "run_paper_ops_daily_bundle",
    "run_paper_ops_alert_payload",
    "run_paper_ops_scheduled_plan",
    "run_paper_ops_safety_regression",
]


def main() -> None:
    passed, failed = 0, 0
    for mod_name in MODULES:
        try:
            mod = importlib.import_module(mod_name)
            mod.main()
            passed += 1
            print(f"  PASS: {mod_name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {mod_name}: {e}")
    print(f"\nSuite: {passed} passed, {failed} failed out of {len(MODULES)}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
