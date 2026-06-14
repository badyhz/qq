"""Integration test: final governance safety regression."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_governance_freeze.final_governance_safety_regression import run_regression


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"


def test_safety_regression_has_checks():
    items = run_regression()
    assert len(items) >= 5
