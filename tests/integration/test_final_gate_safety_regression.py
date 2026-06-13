"""Test final gate safety regression."""
import pytest, pathlib
from src.runtime_integrations.testnet_final_gate.final_gate_safety_regression import run_regression

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

def test_safety_all_pass():
    checks = run_regression(ROOT)
    failed = [c for c in checks if not c.passed]
    assert len(failed) == 0, f"Failed: {[c.check_id for c in failed]}"

def test_submit_gate_locked():
    checks = run_regression(ROOT)
    locked = [c for c in checks if c.check_id == "submit_gate_locked"]
    assert len(locked) == 1
    assert locked[0].passed is True

def test_cancel_gate_locked():
    checks = run_regression(ROOT)
    locked = [c for c in checks if c.check_id == "cancel_gate_locked"]
    assert len(locked) == 1
    assert locked[0].passed is True
