"""Integration test: adapter spec no-submit safety regression."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.adapter_spec_safety_regression import (
    run_regression, scan_forbidden_imports, scan_forbidden_statuses,
    scan_real_submit_patterns, scan_env_secrets
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
