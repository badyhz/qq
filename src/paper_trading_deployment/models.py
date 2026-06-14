"""Paper trading deployment models."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ServerConfig:
    config_id: str
    created_at: str
    deployment_name: str
    mode: str
    host_alias: str
    repo_path: str
    scanner_path: str
    paper_positions_path: str
    reports_dir: str
    logs_dir: str
    schedule: dict
    safety_flags: dict[str, bool]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id, "created_at": self.created_at,
            "deployment_name": self.deployment_name, "mode": self.mode,
            "host_alias": self.host_alias, "repo_path": self.repo_path,
            "scanner_path": self.scanner_path,
            "paper_positions_path": self.paper_positions_path,
            "reports_dir": self.reports_dir, "logs_dir": self.logs_dir,
            "schedule": self.schedule, "safety_flags": self.safety_flags,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class DeploymentPreflightReport:
    report_id: str
    created_at: str
    repo_path: str
    scanner_path: str
    checks_total: int
    checks_passed: int
    checks_failed: int
    warnings: list[str]
    failures: list[str]
    preflight_status: str
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id, "created_at": self.created_at,
            "repo_path": self.repo_path, "scanner_path": self.scanner_path,
            "checks_total": self.checks_total,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "warnings": self.warnings, "failures": self.failures,
            "preflight_status": self.preflight_status,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class CanaryRunReport:
    canary_id: str
    created_at: str
    steps_total: int
    steps_passed: int
    steps_failed: int
    failed_steps: list[str]
    canary_status: str
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "canary_id": self.canary_id, "created_at": self.created_at,
            "steps_total": self.steps_total,
            "steps_passed": self.steps_passed,
            "steps_failed": self.steps_failed,
            "failed_steps": self.failed_steps,
            "canary_status": self.canary_status,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class InstallPlan:
    plan_id: str
    created_at: str
    systemd_files: tuple[str, ...]
    timer_files: tuple[str, ...]
    cron_example: str
    logrotate_example: str
    pre_install_checks: tuple[str, ...]
    install_commands: str
    enable_commands: str
    rollback_commands: str
    manual_confirmation_required: bool
    auto_install: bool
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id, "created_at": self.created_at,
            "systemd_files": list(self.systemd_files),
            "timer_files": list(self.timer_files),
            "cron_example": self.cron_example,
            "logrotate_example": self.logrotate_example,
            "pre_install_checks": list(self.pre_install_checks),
            "install_commands": self.install_commands,
            "enable_commands": self.enable_commands,
            "rollback_commands": self.rollback_commands,
            "manual_confirmation_required": self.manual_confirmation_required,
            "auto_install": self.auto_install,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class RuntimeLayoutReport:
    layout_id: str
    created_at: str
    required_dirs: list[str]
    existing_dirs: list[str]
    missing_dirs: list[str]
    creatable_dirs: list[str]
    layout_status: str
    notes: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "layout_id": self.layout_id, "created_at": self.created_at,
            "required_dirs": self.required_dirs,
            "existing_dirs": self.existing_dirs,
            "missing_dirs": self.missing_dirs,
            "creatable_dirs": self.creatable_dirs,
            "layout_status": self.layout_status,
            "notes": self.notes,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class ServerHealthReport:
    health_id: str
    created_at: str
    server_alias: str
    repo_path: str
    scanner_path: str
    preflight_status: str
    runtime_layout_status: str
    paper_ops_status: str
    strategy_quality_status: str
    health_score: int
    health_status: str
    recommended_actions: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "health_id": self.health_id, "created_at": self.created_at,
            "server_alias": self.server_alias,
            "repo_path": self.repo_path, "scanner_path": self.scanner_path,
            "preflight_status": self.preflight_status,
            "runtime_layout_status": self.runtime_layout_status,
            "paper_ops_status": self.paper_ops_status,
            "strategy_quality_status": self.strategy_quality_status,
            "health_score": self.health_score,
            "health_status": self.health_status,
            "recommended_actions": self.recommended_actions,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class RollbackPlan:
    plan_id: str
    created_at: str
    disable_timer_commands: str
    stop_service_commands: str
    remove_systemd_files_commands: str
    daemon_reload_command: str
    restore_commit_command: str
    preserve_data_command: str
    preserve_reports_command: str
    manual_confirmation_required: bool
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id, "created_at": self.created_at,
            "disable_timer_commands": self.disable_timer_commands,
            "stop_service_commands": self.stop_service_commands,
            "remove_systemd_files_commands": self.remove_systemd_files_commands,
            "daemon_reload_command": self.daemon_reload_command,
            "restore_commit_command": self.restore_commit_command,
            "preserve_data_command": self.preserve_data_command,
            "preserve_reports_command": self.preserve_reports_command,
            "manual_confirmation_required": self.manual_confirmation_required,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class DeploymentSafetyReport:
    report_id: str
    created_at: str
    checks: tuple
    total_checked: int
    total_clean: int
    total_flagged: int
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id, "created_at": self.created_at,
            "checks": [c if isinstance(c, dict) else c.to_dict() for c in self.checks],
            "total_checked": self.total_checked,
            "total_clean": self.total_clean,
            "total_flagged": self.total_flagged,
            "final_verdict": self.final_verdict,
        }
