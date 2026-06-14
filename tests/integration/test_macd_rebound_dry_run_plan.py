"""Integration test: MACD rebound dry-run plan."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.external_scanner_integrations.macd_rebound_dry_run_plan import create_dry_run_plan, render_report

FIXTURE = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "macd_rebound_scanner")


def test_plan_steps() -> None:
    plan = create_dry_run_plan(FIXTURE)
    assert len(plan.steps) == 9


def test_plan_verdict() -> None:
    plan = create_dry_run_plan(FIXTURE)
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in plan.final_verdict


def test_plan_all_readonly() -> None:
    plan = create_dry_run_plan(FIXTURE)
    for s in plan.steps:
        assert "readonly" in s.risk.lower() or "dry" in s.risk.lower() or "LOW" in s.risk


def test_render_report() -> None:
    plan = create_dry_run_plan(FIXTURE)
    md = render_report(plan)
    assert "# MACD Rebound Dry-Run Plan" in md


def main() -> None:
    test_plan_steps()
    test_plan_verdict()
    test_plan_all_readonly()
    test_render_report()
    print("test_macd_rebound_dry_run_plan: ALL PASS")


if __name__ == "__main__":
    main()
