"""Integration test: paper ops deployment full pipeline."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.server_config import build_server_config
from src.paper_trading_deployment.preflight_check import run_preflight
from src.paper_trading_deployment.canary_runner import run_canary
from src.paper_trading_deployment.install_plan import create_install_plan
from src.paper_trading_deployment.runtime_layout import check_layout
from src.paper_trading_deployment.server_health_report import generate_health_report
from src.paper_trading_deployment.rollback_plan import create_rollback_plan
from src.paper_trading_deployment.deployment_safety_regression import run_safety_regression

ROOT = str(pathlib.Path(__file__).resolve().parent.parent.parent)
FIXTURE_CFG = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_deployment" / "config" / "paper_trading_ops_server.example.yaml")


def test_full_pipeline() -> None:
    # Config
    cfg = build_server_config(FIXTURE_CFG)
    assert cfg.deployment_name
    for v in cfg.safety_flags.values():
        assert v is False

    # Preflight
    preflight = run_preflight(cfg.repo_path, cfg.scanner_path)
    assert preflight.preflight_status in ("PASS", "FAIL")

    # Canary
    canary = run_canary()
    assert canary.canary_status == "PASS", f"Failed: {canary.failed_steps}"

    # Install plan
    plan = create_install_plan()
    assert plan.auto_install is False
    assert plan.manual_confirmation_required is True

    # Runtime layout
    layout = check_layout(ROOT)
    assert layout.layout_status in ("READY", "CREATABLE", "INCOMPLETE")

    # Health report
    health = generate_health_report()
    assert health.health_score >= 0

    # Rollback plan
    rollback = create_rollback_plan()
    assert rollback.manual_confirmation_required is True

    # Safety regression
    safety = run_safety_regression()
    assert safety.total_flagged == 0


def test_all_verdicts_contain_safety() -> None:
    cfg = build_server_config(FIXTURE_CFG)
    preflight = run_preflight(cfg.repo_path, cfg.scanner_path)
    canary = run_canary()
    plan = create_install_plan()
    layout = check_layout(ROOT)
    health = generate_health_report()
    rollback = create_rollback_plan()
    safety = run_safety_regression()

    for verdict in [cfg.final_verdict, preflight.final_verdict, canary.final_verdict,
                    plan.final_verdict, layout.final_verdict, health.final_verdict,
                    rollback.final_verdict, safety.final_verdict]:
        assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in verdict, f"Missing safety in: {verdict}"


def main() -> None:
    test_full_pipeline()
    test_all_verdicts_contain_safety()
    print("test_paper_ops_deployment_suite: ALL PASS")


if __name__ == "__main__":
    main()
