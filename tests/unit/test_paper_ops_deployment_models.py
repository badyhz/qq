"""Unit test: paper trading deployment models."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.models import (
    new_id, utc_now_iso, ServerConfig, DeploymentPreflightReport,
    CanaryRunReport, InstallPlan, RuntimeLayoutReport,
    ServerHealthReport, RollbackPlan, DeploymentSafetyReport,
)


def test_new_id() -> None:
    assert new_id("T").startswith("T_")
    assert len(new_id("T")) == 14


def test_utc_now_iso() -> None:
    ts = utc_now_iso()
    assert "T" in ts


def test_server_config_to_dict() -> None:
    c = ServerConfig(config_id="SCF_test", created_at="2026-01-01T00:00:00+00:00",
        deployment_name="test", mode="dry_run_only", host_alias="test",
        repo_path="/tmp", scanner_path="/tmp", paper_positions_path="data/x",
        reports_dir="reports/x", logs_dir="logs/x", schedule={},
        safety_flags={"real_order_submit_allowed": False},
        final_verdict="OK")
    assert c.to_dict()["deployment_name"] == "test"


def test_preflight_report_to_dict() -> None:
    r = DeploymentPreflightReport(report_id="DPR_test", created_at="2026-01-01T00:00:00+00:00",
        repo_path="/tmp", scanner_path="/tmp", checks_total=5, checks_passed=5,
        checks_failed=0, warnings=[], failures=[], preflight_status="PASS",
        final_verdict="OK")
    assert r.to_dict()["preflight_status"] == "PASS"


def test_canary_report_to_dict() -> None:
    r = CanaryRunReport(canary_id="CNR_test", created_at="2026-01-01T00:00:00+00:00",
        steps_total=9, steps_passed=9, steps_failed=0, failed_steps=[],
        canary_status="PASS", final_verdict="OK")
    assert r.to_dict()["canary_status"] == "PASS"


def test_install_plan_to_dict() -> None:
    p = InstallPlan(plan_id="IPL_test", created_at="2026-01-01T00:00:00+00:00",
        systemd_files=("a.service",), timer_files=("a.timer",),
        cron_example="x", logrotate_example="y", pre_install_checks=("check",),
        install_commands="cmd", enable_commands="cmd", rollback_commands="cmd",
        manual_confirmation_required=True, auto_install=False, final_verdict="OK")
    d = p.to_dict()
    assert d["auto_install"] is False
    assert d["manual_confirmation_required"] is True


def test_runtime_layout_to_dict() -> None:
    r = RuntimeLayoutReport(layout_id="RLR_test", created_at="2026-01-01T00:00:00+00:00",
        required_dirs=["a"], existing_dirs=["a"], missing_dirs=[], creatable_dirs=[],
        layout_status="READY", notes=[], final_verdict="OK")
    assert r.to_dict()["layout_status"] == "READY"


def test_server_health_to_dict() -> None:
    r = ServerHealthReport(health_id="SHR_test", created_at="2026-01-01T00:00:00+00:00",
        server_alias="test", repo_path="/tmp", scanner_path="/tmp",
        preflight_status="PASS", runtime_layout_status="READY",
        paper_ops_status="HEALTHY", strategy_quality_status="PROMISING",
        health_score=90, health_status="HEALTHY",
        recommended_actions=["monitor"], final_verdict="OK")
    assert r.to_dict()["health_score"] == 90


def test_rollback_plan_to_dict() -> None:
    p = RollbackPlan(plan_id="RBP_test", created_at="2026-01-01T00:00:00+00:00",
        disable_timer_commands="cmd", stop_service_commands="cmd",
        remove_systemd_files_commands="cmd", daemon_reload_command="cmd",
        restore_commit_command="cmd", preserve_data_command="cmd",
        preserve_reports_command="cmd", manual_confirmation_required=True,
        final_verdict="OK")
    assert p.to_dict()["manual_confirmation_required"] is True


def test_deployment_safety_to_dict() -> None:
    r = DeploymentSafetyReport(report_id="DSR_test", created_at="2026-01-01T00:00:00+00:00",
        checks=(), total_checked=0, total_clean=0, total_flagged=0,
        final_verdict="OK")
    assert r.to_dict()["total_flagged"] == 0


def main() -> None:
    test_new_id()
    test_utc_now_iso()
    test_server_config_to_dict()
    test_preflight_report_to_dict()
    test_canary_report_to_dict()
    test_install_plan_to_dict()
    test_runtime_layout_to_dict()
    test_server_health_to_dict()
    test_rollback_plan_to_dict()
    test_deployment_safety_to_dict()
    print("test_paper_ops_deployment_models: ALL PASS")


if __name__ == "__main__":
    main()
