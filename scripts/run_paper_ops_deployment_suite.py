"""Paper ops deployment suite runner — executes all deployment modules."""
from __future__ import annotations
import importlib, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
ROOT = pathlib.Path(__file__).resolve().parent.parent

MODULES = [
    "run_paper_ops_server_config_check",
    "run_paper_ops_deployment_preflight",
    "run_paper_ops_canary_dry_run",
    "run_paper_ops_install_plan",
    "run_paper_ops_runtime_layout_check",
    "run_paper_ops_server_health_report",
    "run_paper_ops_rollback_plan",
    "run_paper_ops_deployment_safety_regression",
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
    if failed == 0:
        print("PAPER_OPS_DEPLOYMENT_SUITE_PASS")
    print("REAL_ORDER_SUBMIT_NOT_ALLOWED")
    print("REAL_TRADING_NOT_ALLOWED")
    print("NO_SYSTEMD_AUTO_INSTALL")
    print("NO_CRONTAB_AUTO_WRITE")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
