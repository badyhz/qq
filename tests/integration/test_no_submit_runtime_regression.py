"""Integration tests for no-submit runtime regression."""
from __future__ import annotations
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.safety.no_submit_regression import run_safety_checks


def test_all_safety_checks_pass():
    checks = run_safety_checks(ROOT / "data", ROOT / "reports")
    for c in checks:
        assert c.passed, f"Failed: {c.check_id} - {c.detail}"


def test_no_high_risk_imports():
    checks = run_safety_checks(ROOT / "data", ROOT / "reports")
    import_checks = [c for c in checks if c.check_id.startswith("no_import_")]
    assert len(import_checks) > 0
    assert all(c.passed for c in import_checks)
