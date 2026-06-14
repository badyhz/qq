"""Unit test: paper ops rollback plan."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.rollback_plan import create_rollback_plan


def test_rollback_manual_confirmation() -> None:
    plan = create_rollback_plan()
    assert plan.manual_confirmation_required is True


def test_rollback_has_commands() -> None:
    plan = create_rollback_plan()
    assert "systemctl" in plan.disable_timer_commands
    assert "systemctl" in plan.stop_service_commands
    assert "daemon-reload" in plan.daemon_reload_command


def test_rollback_verdict_format() -> None:
    plan = create_rollback_plan()
    assert "PAPER_OPS_ROLLBACK_PLAN_READY" in plan.final_verdict
    assert "manual_confirmation_required=true" in plan.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in plan.final_verdict


def test_rollback_to_dict() -> None:
    plan = create_rollback_plan()
    d = plan.to_dict()
    assert d["manual_confirmation_required"] is True
    assert "disable_timer_commands" in d


def main() -> None:
    test_rollback_manual_confirmation()
    test_rollback_has_commands()
    test_rollback_verdict_format()
    test_rollback_to_dict()
    print("test_paper_ops_rollback_plan: ALL PASS")


if __name__ == "__main__":
    main()
