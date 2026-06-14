"""Paper trading pipeline models."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ScannerLogSnapshot:
    snapshot_id: str
    scanner_path: str
    signals_count: int
    alerts_count: int
    scan_detail_count: int
    errors_count: int
    latest_signal_time: str | None
    latest_alert_time: str | None
    source_files: dict[str, bool]
    source_status: str
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id, "scanner_path": self.scanner_path,
            "signals_count": self.signals_count, "alerts_count": self.alerts_count,
            "scan_detail_count": self.scan_detail_count, "errors_count": self.errors_count,
            "latest_signal_time": self.latest_signal_time,
            "latest_alert_time": self.latest_alert_time,
            "source_files": self.source_files, "source_status": self.source_status,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class DedupedSignalBatch:
    batch_id: str
    created_at: str
    raw_count: int
    deduped_count: int
    duplicate_count: int
    cooldown_filtered_count: int
    force_alert_count: int
    signals: tuple[dict, ...]
    dedup_notes: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id, "created_at": self.created_at,
            "raw_count": self.raw_count, "deduped_count": self.deduped_count,
            "duplicate_count": self.duplicate_count,
            "cooldown_filtered_count": self.cooldown_filtered_count,
            "force_alert_count": self.force_alert_count,
            "signals": list(self.signals),
            "dedup_notes": self.dedup_notes,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class TradePlanBatch:
    batch_id: str
    created_at: str
    source_snapshot_id: str
    total_signals: int
    plans_created: int
    plans_rejected: int
    plans: tuple[dict, ...]
    rejection_reasons: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id, "created_at": self.created_at,
            "source_snapshot_id": self.source_snapshot_id,
            "total_signals": self.total_signals,
            "plans_created": self.plans_created,
            "plans_rejected": self.plans_rejected,
            "plans": list(self.plans),
            "rejection_reasons": self.rejection_reasons,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class PaperPositionRecord:
    record_id: str
    paper_position_id: str
    plan_id: str
    symbol: str
    timeframe: str
    status: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    created_at: str
    updated_at: str
    source_signal_id: str
    dry_run_only: bool

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "paper_position_id": self.paper_position_id,
            "plan_id": self.plan_id, "symbol": self.symbol,
            "timeframe": self.timeframe, "status": self.status,
            "entry_price": self.entry_price, "stop_loss": self.stop_loss,
            "take_profit_1": self.take_profit_1,
            "take_profit_2": self.take_profit_2,
            "take_profit_3": self.take_profit_3,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "source_signal_id": self.source_signal_id,
            "dry_run_only": self.dry_run_only,
        }


@dataclass(frozen=True)
class ReplaySchedule:
    schedule_id: str
    created_at: str
    total_positions: int
    needs_entry_check: int
    needs_exit_check: int
    already_closed: int
    stale_positions: int
    next_actions: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id, "created_at": self.created_at,
            "total_positions": self.total_positions,
            "needs_entry_check": self.needs_entry_check,
            "needs_exit_check": self.needs_exit_check,
            "already_closed": self.already_closed,
            "stale_positions": self.stale_positions,
            "next_actions": self.next_actions,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class DailyPaperReview:
    review_id: str
    created_at: str
    date: str
    raw_signals: int
    deduped_signals: int
    trade_plans_created: int
    paper_positions_total: int
    paper_open_count: int
    paper_closed_count: int
    tp1_count: int
    tp2_count: int
    tp3_count: int
    stop_count: int
    time_stop_count: int
    win_rate_placeholder: float
    expectancy_r_placeholder: float
    top_symbols: list[str]
    risk_notes: list[str]
    data_quality_notes: list[str]
    next_actions: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id, "created_at": self.created_at,
            "date": self.date, "raw_signals": self.raw_signals,
            "deduped_signals": self.deduped_signals,
            "trade_plans_created": self.trade_plans_created,
            "paper_positions_total": self.paper_positions_total,
            "paper_open_count": self.paper_open_count,
            "paper_closed_count": self.paper_closed_count,
            "tp1_count": self.tp1_count, "tp2_count": self.tp2_count,
            "tp3_count": self.tp3_count, "stop_count": self.stop_count,
            "time_stop_count": self.time_stop_count,
            "win_rate_placeholder": self.win_rate_placeholder,
            "expectancy_r_placeholder": self.expectancy_r_placeholder,
            "top_symbols": self.top_symbols, "risk_notes": self.risk_notes,
            "data_quality_notes": self.data_quality_notes,
            "next_actions": self.next_actions,
            "final_verdict": self.final_verdict,
        }


@dataclass(frozen=True)
class FeishuPaperReviewPayload:
    payload_id: str
    created_at: str
    title: str
    date: str
    raw_signals: int
    deduped_signals: int
    trade_plans_created: int
    paper_open_count: int
    paper_closed_count: int
    tp_hit_count: int
    stop_count: int
    top_symbols: list[str]
    risk_notes: list[str]
    next_actions: list[str]
    dry_run_only: bool
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "payload_id": self.payload_id, "created_at": self.created_at,
            "title": self.title, "date": self.date,
            "raw_signals": self.raw_signals, "deduped_signals": self.deduped_signals,
            "trade_plans_created": self.trade_plans_created,
            "paper_open_count": self.paper_open_count,
            "paper_closed_count": self.paper_closed_count,
            "tp_hit_count": self.tp_hit_count, "stop_count": self.stop_count,
            "top_symbols": self.top_symbols, "risk_notes": self.risk_notes,
            "next_actions": self.next_actions, "dry_run_only": self.dry_run_only,
            "final_verdict": self.final_verdict,
        }
