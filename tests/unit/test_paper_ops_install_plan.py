"""Unit test: paper ops install plan."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.install_plan import create_install_plan


def test_install_auto_install_false() -> None:
    plan = create_install_plan()
    assert plan.auto_install is False


def test_install_manual_confirmation() -> None:
    plan = create_install_plan()
    assert plan.manual_confirmation_required is True


def test_install_has_systemd_files() -> None:
    plan = create_install_plan()
    assert len(plan.systemd_files) >= 6


def test_install_has_timer_files() -> None:
    plan = create_install_plan()
    assert len(plan.timer_files) >= 3


def test_install_verdict_format() -> None:
    plan = create_install_plan()
    assert "PAPER_OPS_INSTALL_PLAN_READY" in plan.final_verdict
    assert "auto_install=false" in plan.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in plan.final_verdict


def test_install_to_dict() -> None:
    plan = create_install_plan()
    d = plan.to_dict()
    assert d["auto_install"] is False
    assert d["manual_confirmation_required"] is True


def main() -> None:
    test_install_auto_install_false()
    test_install_manual_confirmation()
    test_install_has_systemd_files()
    test_install_has_timer_files()
    test_install_verdict_format()
    test_install_to_dict()
    print("test_paper_ops_install_plan: ALL PASS")


if __name__ == "__main__":
    main()
