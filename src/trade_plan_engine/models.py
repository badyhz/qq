"""Core models for trade plan engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass(frozen=True)
class SignalCandidate:
    signal_id: str
    symbol: str
    timeframe: str
    signal_time: str
    price: float
    signal_level: str
    drop_pct: float
    macd_dif: float
    macd_dea: float
    macd_hist: float
    ma7: float
    ma25: float
    ma99: float
    volume: float
    volume_ma5: float
    volume_ratio: float
    above_ma99: bool
    reason: str
    source: str = "macd_rebound_scanner"

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id, "symbol": self.symbol,
            "timeframe": self.timeframe, "signal_time": self.signal_time,
            "price": self.price, "signal_level": self.signal_level,
            "drop_pct": self.drop_pct, "macd_dif": self.macd_dif,
            "macd_dea": self.macd_dea, "macd_hist": self.macd_hist,
            "ma7": self.ma7, "ma25": self.ma25, "ma99": self.ma99,
            "volume": self.volume, "volume_ma5": self.volume_ma5,
            "volume_ratio": self.volume_ratio, "above_ma99": self.above_ma99,
            "reason": self.reason, "source": self.source,
        }


@dataclass(frozen=True)
class TradePlan:
    plan_id: str
    signal_id: str
    symbol: str
    timeframe: str
    side: str
    entry_type: str
    entry_price: float
    entry_zone_low: float
    entry_zone_high: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_pct: float
    reward_risk_1: float
    reward_risk_2: float
    reward_risk_3: float
    position_size_hint: float
    max_account_risk_pct: float
    plan_grade: str
    valid_until: str
    invalid_if: str
    explain: str
    dry_run_only: bool = True

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id, "signal_id": self.signal_id,
            "symbol": self.symbol, "timeframe": self.timeframe,
            "side": self.side, "entry_type": self.entry_type,
            "entry_price": self.entry_price,
            "entry_zone_low": self.entry_zone_low,
            "entry_zone_high": self.entry_zone_high,
            "stop_loss": self.stop_loss,
            "take_profit_1": self.take_profit_1,
            "take_profit_2": self.take_profit_2,
            "take_profit_3": self.take_profit_3,
            "risk_pct": self.risk_pct,
            "reward_risk_1": self.reward_risk_1,
            "reward_risk_2": self.reward_risk_2,
            "reward_risk_3": self.reward_risk_3,
            "position_size_hint": self.position_size_hint,
            "max_account_risk_pct": self.max_account_risk_pct,
            "plan_grade": self.plan_grade, "valid_until": self.valid_until,
            "invalid_if": self.invalid_if, "explain": self.explain,
            "dry_run_only": self.dry_run_only,
        }


@dataclass(frozen=True)
class RiskPlan:
    risk_plan_id: str
    account_equity_placeholder: float
    max_account_risk_pct: float
    risk_per_trade_pct: float
    entry_price: float
    stop_loss: float
    risk_per_unit: float
    suggested_notional: float
    suggested_quantity_placeholder: float
    leverage_hint: int
    risk_level: str
    risk_notes: str

    def to_dict(self) -> dict:
        return {
            "risk_plan_id": self.risk_plan_id,
            "account_equity_placeholder": self.account_equity_placeholder,
            "max_account_risk_pct": self.max_account_risk_pct,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "entry_price": self.entry_price, "stop_loss": self.stop_loss,
            "risk_per_unit": self.risk_per_unit,
            "suggested_notional": self.suggested_notional,
            "suggested_quantity_placeholder": self.suggested_quantity_placeholder,
            "leverage_hint": self.leverage_hint,
            "risk_level": self.risk_level, "risk_notes": self.risk_notes,
        }


@dataclass(frozen=True)
class ExitPlan:
    exit_plan_id: str
    stop_loss_rule: str
    tp1_rule: str
    tp2_rule: str
    tp3_rule: str
    time_stop_rule: str
    signal_failure_rule: str
    trailing_stop_rule: str
    manual_review_required: bool

    def to_dict(self) -> dict:
        return {
            "exit_plan_id": self.exit_plan_id,
            "stop_loss_rule": self.stop_loss_rule,
            "tp1_rule": self.tp1_rule, "tp2_rule": self.tp2_rule,
            "tp3_rule": self.tp3_rule, "time_stop_rule": self.time_stop_rule,
            "signal_failure_rule": self.signal_failure_rule,
            "trailing_stop_rule": self.trailing_stop_rule,
            "manual_review_required": self.manual_review_required,
        }


@dataclass
class PaperPosition:
    paper_position_id: str
    plan_id: str
    symbol: str
    side: str
    status: str
    paper_entry_price: float
    paper_entry_time: str
    paper_stop_loss: float
    paper_take_profit_1: float
    paper_take_profit_2: float
    paper_take_profit_3: float
    paper_exit_price: float
    paper_exit_time: str
    paper_exit_reason: str
    paper_pnl_r: float
    paper_pnl_pct: float
    bars_held: int
    dry_run_only: bool = True

    def to_dict(self) -> dict:
        return {
            "paper_position_id": self.paper_position_id,
            "plan_id": self.plan_id, "symbol": self.symbol,
            "side": self.side, "status": self.status,
            "paper_entry_price": self.paper_entry_price,
            "paper_entry_time": self.paper_entry_time,
            "paper_stop_loss": self.paper_stop_loss,
            "paper_take_profit_1": self.paper_take_profit_1,
            "paper_take_profit_2": self.paper_take_profit_2,
            "paper_take_profit_3": self.paper_take_profit_3,
            "paper_exit_price": self.paper_exit_price,
            "paper_exit_time": self.paper_exit_time,
            "paper_exit_reason": self.paper_exit_reason,
            "paper_pnl_r": self.paper_pnl_r,
            "paper_pnl_pct": self.paper_pnl_pct,
            "bars_held": self.bars_held,
            "dry_run_only": self.dry_run_only,
        }


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
