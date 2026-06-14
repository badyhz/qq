"""Unit test: paper ops scheduled run plan."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.scheduled_run_plan import create_scheduled_plan


def test_plan_has_tasks() -> None:
    plan = create_scheduled_plan()
    assert len(plan.tasks) >= 4


def test_plan_has_cron() -> None:
    plan = create_scheduled_plan()
    assert "*/15" in plan.cron_template
    assert "*/30" in plan.cron_template
    assert "23:55" in plan.cron_template or "55 23" in plan.cron_template


def test_plan_has_systemd() -> None:
    plan = create_scheduled_plan()
    assert "[Unit]" in plan.systemd_template
    assert "[Service]" in plan.systemd_template
    assert "[Timer]" in plan.systemd_template


def test_plan_verdict_format() -> None:
    plan = create_scheduled_plan()
    assert "PAPER_OPS_SCHEDULED_RUN_PLAN_READY" in plan.final_verdict
    assert "TEMPLATES_ONLY" in plan.final_verdict
    assert "NOT_INSTALLED" in plan.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in plan.final_verdict


def test_plan_to_dict() -> None:
    plan = create_scheduled_plan()
    d = plan.to_dict()
    assert "plan_id" in d
    assert "cron_template" in d
    assert "systemd_template" in d


def main() -> None:
    test_plan_has_tasks()
    test_plan_has_cron()
    test_plan_has_systemd()
    test_plan_verdict_format()
    test_plan_to_dict()
    print("test_paper_ops_scheduled_plan: ALL PASS")


if __name__ == "__main__":
    main()
