"""Paper trading ops models."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class LogFreshnessReport:
    report_id: str
    created_at: str
    scanner_path: str
    signals_file_exists: bool
    alerts_file_exists: bool
    scan_detail_file_exists: bool
    errors_file_exists: bool
    latest_signal_time: str | None
    latest_alert_time: str | None
    latest_scan_detail_time: str | None
    minutes_since_latest_signal: float | None
    minutes_since_latest_alert: float | None
    minutes_since_latest_scan_detail: float | None
    freshness_status: str
    stale_reasons: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id, "created_at": self.created_at,
            "scanner_path": self.scanner_path,
            "signals_file_exists": self.signals_file_exists,
            "alerts_file_exists": self.alerts_file_exists,
            "scan_detail_file_exists": self.scan_detail_file_exists,
            "errors_file_exists": self.errors_file_exists,
            "latest_signal_time": self.latest_signal_time,
            "latest_alert_time": self.latest_alert_time,
            "latest_scan_detail_time": self.latest_scan_detail_time,
            "minutes_since_latest_signal": self.minutes_since_latest_signal,
            "minutes_since_latest_alert": self.minutes_since_latest_alert,
            "minutes_since_latest_scan_detail": self.minutes_since_latest_scan_detail,
            "freshness_status": self.freshness_status,
            "stale_reasons": self.stale_reasons,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class PaperStateAudit:
    audit_id: str
    created_at: str
    store_path: str
    records_total: int
    duplicate_plan_ids: int
    duplicate_position_ids: int
    invalid_status_count: int
    not_dry_run_count: int
    stale_open_count: int
    stale_planned_count: int
    missing_price_field_count: int
    audit_status: str
    audit_notes: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id, "created_at": self.created_at,
            "store_path": self.store_path, "records_total": self.records_total,
            "duplicate_plan_ids": self.duplicate_plan_ids,
            "duplicate_position_ids": self.duplicate_position_ids,
            "invalid_status_count": self.invalid_status_count,
            "not_dry_run_count": self.not_dry_run_count,
            "stale_open_count": self.stale_open_count,
            "stale_planned_count": self.stale_planned_count,
            "missing_price_field_count": self.missing_price_field_count,
            "audit_status": self.audit_status,
            "audit_notes": self.audit_notes,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class StrategyQualityMetrics:
    metrics_id: str
    created_at: str
    total_positions: int
    closed_positions: int
    open_positions: int
    tp1_count: int
    tp2_count: int
    tp3_count: int
    stop_count: int
    time_stop_count: int
    win_count: int
    loss_count: int
    win_rate: float
    avg_pnl_r: float
    median_pnl_r: float
    expectancy_r: float
    best_pnl_r: float
    worst_pnl_r: float
    profit_factor_placeholder: float
    avg_bars_held: float
    max_bars_held: int
    symbol_breakdown: dict[str, dict]
    sample_status: str
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "metrics_id": self.metrics_id, "created_at": self.created_at,
            "total_positions": self.total_positions,
            "closed_positions": self.closed_positions,
            "open_positions": self.open_positions,
            "tp1_count": self.tp1_count, "tp2_count": self.tp2_count,
            "tp3_count": self.tp3_count, "stop_count": self.stop_count,
            "time_stop_count": self.time_stop_count,
            "win_count": self.win_count, "loss_count": self.loss_count,
            "win_rate": self.win_rate, "avg_pnl_r": self.avg_pnl_r,
            "median_pnl_r": self.median_pnl_r,
            "expectancy_r": self.expectancy_r,
            "best_pnl_r": self.best_pnl_r, "worst_pnl_r": self.worst_pnl_r,
            "profit_factor_placeholder": self.profit_factor_placeholder,
            "avg_bars_held": self.avg_bars_held,
            "max_bars_held": self.max_bars_held,
            "symbol_breakdown": self.symbol_breakdown,
            "sample_status": self.sample_status,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class SignalQualityDashboard:
    dashboard_id: str
    created_at: str
    period: str
    raw_signals: int
    deduped_signals: int
    plans_created: int
    plans_rejected: int
    paper_positions_total: int
    open_positions: int
    closed_positions: int
    tp_hit_count: int
    stop_count: int
    top_symbols_by_signal: list[str]
    top_symbols_by_tp: list[str]
    top_symbols_by_stop: list[str]
    best_symbols: list[str]
    worst_symbols: list[str]
    quality_grade: str
    quality_notes: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "dashboard_id": self.dashboard_id, "created_at": self.created_at,
            "period": self.period, "raw_signals": self.raw_signals,
            "deduped_signals": self.deduped_signals,
            "plans_created": self.plans_created,
            "plans_rejected": self.plans_rejected,
            "paper_positions_total": self.paper_positions_total,
            "open_positions": self.open_positions,
            "closed_positions": self.closed_positions,
            "tp_hit_count": self.tp_hit_count, "stop_count": self.stop_count,
            "top_symbols_by_signal": self.top_symbols_by_signal,
            "top_symbols_by_tp": self.top_symbols_by_tp,
            "top_symbols_by_stop": self.top_symbols_by_stop,
            "best_symbols": self.best_symbols,
            "worst_symbols": self.worst_symbols,
            "quality_grade": self.quality_grade,
            "quality_notes": self.quality_notes,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class DailyOpsBundle:
    bundle_id: str
    created_at: str
    date: str
    freshness_status: str
    paper_state_status: str
    strategy_sample_status: str
    dashboard_grade: str
    critical_alerts: list[str]
    warnings: list[str]
    recommended_actions: list[str]
    operator_checklist: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id, "created_at": self.created_at,
            "date": self.date, "freshness_status": self.freshness_status,
            "paper_state_status": self.paper_state_status,
            "strategy_sample_status": self.strategy_sample_status,
            "dashboard_grade": self.dashboard_grade,
            "critical_alerts": self.critical_alerts,
            "warnings": self.warnings,
            "recommended_actions": self.recommended_actions,
            "operator_checklist": self.operator_checklist,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class ScheduledRunPlan:
    plan_id: str
    created_at: str
    tasks: tuple[dict, ...]
    cron_template: str
    systemd_template: str
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id, "created_at": self.created_at,
            "tasks": list(self.tasks), "cron_template": self.cron_template,
            "systemd_template": self.systemd_template,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class OpsAlertPayload:
    payload_id: str
    created_at: str
    title: str
    date: str
    freshness_status: str
    paper_state_status: str
    strategy_sample_status: str
    dashboard_grade: str
    critical_alerts: list[str]
    warnings: list[str]
    recommended_actions: list[str]
    dry_run_only: bool
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "payload_id": self.payload_id, "created_at": self.created_at,
            "title": self.title, "date": self.date,
            "freshness_status": self.freshness_status,
            "paper_state_status": self.paper_state_status,
            "strategy_sample_status": self.strategy_sample_status,
            "dashboard_grade": self.dashboard_grade,
            "critical_alerts": self.critical_alerts,
            "warnings": self.warnings,
            "recommended_actions": self.recommended_actions,
            "dry_run_only": self.dry_run_only,
            "final_verdict": self.final_verdict,
        }
