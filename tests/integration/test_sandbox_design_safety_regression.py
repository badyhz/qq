"""Test sandbox design safety regression."""
import pytest, pathlib
from src.runtime_integrations.testnet_sandbox.sandbox_design_safety_regression import run_safety_regression

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def test_safety_regression_all_pass():
    checks = run_safety_regression(ROOT)
    failed = [c for c in checks if not c.passed]
    assert len(failed) == 0, f"Failed checks: {[c.check_id for c in failed]}"


def test_no_high_risk_imports():
    checks = run_safety_regression(ROOT)
    high_risk = [c for c in checks if "no_core_live_runner" in c.check_id or "no_scripts_live_playbook" in c.check_id]
    assert all(c.passed for c in high_risk)


def test_no_forbidden_imports():
    checks = run_safety_regression(ROOT)
    forbidden = [c for c in checks if "no_import_ccxt" in c.check_id or "no_import_requests" in c.check_id]
    assert all(c.passed for c in forbidden)
