"""Integration test: read-only preapproval safety regression."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_preapproval.preapproval_safety_regression import (
    run_regression, scan_forbidden_imports, scan_forbidden_statuses,
    scan_real_submit_patterns, scan_env_secrets, scan_gate_unlock_markers,
    scan_real_endpoints
)


def test_safety_regression_all_pass():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Failed checks: {[i.check_id for i in failed]}"


def test_no_forbidden_imports():
    items = scan_forbidden_imports()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0


def test_no_forbidden_statuses():
    items = scan_forbidden_statuses()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0


def test_no_real_submit_patterns():
    items = scan_real_submit_patterns()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0


def test_no_env_secrets():
    items = scan_env_secrets()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0


def test_no_gate_unlock_markers():
    items = scan_gate_unlock_markers()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0


def test_no_real_endpoints():
    items = scan_real_endpoints()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0
