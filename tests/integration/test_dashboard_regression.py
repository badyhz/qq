"""Integration tests for dashboard regression."""
from __future__ import annotations
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.operator.dashboard_regression import check_dashboard


def test_dashboard_regression_all_pass():
    checks = check_dashboard(ROOT / "data" / "runtime" / "operator" / "system_state.json", ROOT / "reports" / "operator_dashboard.html")
    for c in checks:
        assert c.passed, f"Failed: {c.check_name} - {c.detail}"


def test_dashboard_has_safety_banners():
    checks = check_dashboard(ROOT / "data" / "runtime" / "operator" / "system_state.json", ROOT / "reports" / "operator_dashboard.html")
    check_names = {c.check_name for c in checks}
    assert "dashboard_contains_NOT_ALLOWED" in check_names
