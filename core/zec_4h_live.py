"""Deterministic ZECUSDT 4H small-live strategy and local audit artifacts.

The module contains no credential loading and performs no network calls.  It is
safe to exercise with fixtures.  Real account access belongs to the separately
guarded adapter in :mod:`core.zec_4h_live_execution`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from core.paper_trading.data_source import MarketBar, format_utc_timestamp


STRATEGY_ID = "zec_4h_live_v1"
SYMBOL = "ZECUSDT"
TIMEFRAME = "4h"
STARTING_EQUITY = 50.0
TARGET_EQUITY = 150.0
HARD_EQUITY_FLOOR = 30.0
INITIAL_NOTIONAL_BUFFER = 0.96


class StrategyPhase(str, Enum):
    FLAT = "FLAT"
    LONG_FULL = "LONG_FULL"
    LONG_REDUCED = "LONG_REDUCED"
    WAITING_READD = "WAITING_READD"
    HARD_STOP = "HARD_STOP"
    TARGET_REACHED_PAUSED = "TARGET_REACHED_PAUSED"


class LiveAction(str, Enum):
    OPEN = "OPEN"
    REDUCE_50 = "REDUCE_50"
    ADD_50 = "ADD_50"
    STOP_CLOSE = "STOP_CLOSE"
    HARD_STOP_CLOSE = "HARD_STOP_CLOSE"


@dataclass
class StrategyState:
    strategy_id: str = STRATEGY_ID
    symbol: str = SYMBOL
    timeframe: str = TIMEFRAME
    phase: str = StrategyPhase.FLAT.value
    last_signal: str = ""
    last_signal_open: Optional[float] = None
    bars_since_signal: int = 0
    buy_condition_active: bool = False
    sell_condition_active: bool = False
    attack_open: Optional[float] = None
    attack_close: Optional[float] = None
    attack_gain_rate: Optional[float] = None
    attack_bar_close_time: Optional[str] = None
    wait_attack_reduce: bool = False
    wait_add_position: bool = False
    pullback_seen: bool = False
    bars_after_touch: int = 0
    entry_low: Optional[float] = None
    last_processed_bar_close_time: Optional[str] = None
    full_position_qty: float = 0.0
    actual_position_qty: float = 0.0
    reduced_qty: float = 0.0
    pending_action: str = ""
    target_reached: bool = False
    hard_stop_reason: str = ""
    last_hm_bar_close_time: Optional[str] = None
    hm_observation_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Optional[dict[str, Any]]) -> "StrategyState":
        values = dict(raw or {})
        allowed = set(cls.__dataclass_fields__)
        state = cls(**{key: value for key, value in values.items() if key in allowed})
        if state.strategy_id != STRATEGY_ID or state.symbol != SYMBOL or state.timeframe != TIMEFRAME:
            raise ValueError("strategy state identity mismatch")
        if state.phase not in {item.value for item in StrategyPhase}:
            raise ValueError("unknown strategy phase")
        return state


@dataclass(frozen=True)
class StrategyDecision:
    action: Optional[str]
    signal_key: str
    client_order_id: str
    bar_close_time: str
    signal_price: float
    entry_low: Optional[float]
    reason: str
    hm_detected: bool = False
    diagnostics: dict[str, Any] = field(default_factory=dict)


def load_strategy_state(path: Path) -> StrategyState:
    if not path.exists():
        return StrategyState()
    return StrategyState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_strategy_state(path: Path, state: StrategyState) -> None:
    """Atomically persist state so a restart never observes a partial document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _ema(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [float(values[0])]
    for value in values[1:]:
        result.append(alpha * float(value) + (1.0 - alpha) * result[-1])
    return result


def _sma(values: Sequence[float], period: int) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(values)
    running = 0.0
    for index, value in enumerate(values):
        running += float(value)
        if index >= period:
            running -= float(values[index - period])
        if index >= period - 1:
            result[index] = running / period
    return result


def _macd_dif(values: Sequence[float]) -> list[float]:
    return _macd_lines(values)[0]


def _macd_lines(values: Sequence[float]) -> tuple[list[float], list[float]]:
    """Return DIF(EMA12-EMA26) and its EMA9 signal line."""
    fast = _ema(values, 12)
    slow = _ema(values, 26)
    dif = [left - right for left, right in zip(fast, slow)]
    return dif, _ema(dif, 9)


def _bar_close_time(bar: MarketBar) -> str:
    if bar.close_time is None:
        raise ValueError("closed bar is missing close_time")
    if bar.close_time.tzinfo is None or bar.close_time.utcoffset() is None:
        raise ValueError("closed bar close_time must be timezone-aware")
    if bar.provider_closed is not True:
        raise ValueError("strategy only accepts canonical provider_closed bars")
    if str(bar.symbol).upper() != SYMBOL or str(bar.timeframe).lower() != TIMEFRAME:
        raise ValueError("unexpected bar identity")
    return format_utc_timestamp(bar.close_time)


def _is_black_horse(last_three: Sequence[MarketBar]) -> bool:
    if len(last_three) != 3 or not all(item.close > item.open for item in last_three):
        return False
    first, second, third = last_three
    bodies = [abs(item.close - item.open) for item in last_three]
    return (
        bodies[0] < bodies[1] < bodies[2]
        and second.close > first.high
        and third.close > second.high
        and first.high < second.high < third.high
        and first.low < second.low < third.low
        and first.volume < second.volume < third.volume
        and third.volume < second.volume * 2.0
    )


def build_signal_key(action: str, bar_close_time: str) -> str:
    stamp = (
        datetime.fromisoformat(bar_close_time.replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .strftime("%Y%m%dT%H%M%SZ")
    )
    return f"{STRATEGY_ID}:{SYMBOL}:{TIMEFRAME}:{stamp}:{action}"


def build_client_order_id(signal_key: str, action: str, bar_close_time: str) -> str:
    stamp = (
        datetime.fromisoformat(bar_close_time.replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .strftime("%y%m%d%H%M")
    )
    digest = hashlib.sha256(signal_key.encode("utf-8")).hexdigest()[:10]
    action_code = {
        LiveAction.OPEN.value: "op",
        LiveAction.REDUCE_50.value: "r5",
        LiveAction.ADD_50.value: "a5",
        LiveAction.STOP_CLOSE.value: "sc",
        LiveAction.HARD_STOP_CLOSE.value: "hc",
    }[action]
    return f"z4{action_code}{stamp}{digest}"[:35]


def _decision(
    *,
    action: Optional[str],
    bar: MarketBar,
    reason: str,
    entry_low: Optional[float] = None,
    hm_detected: bool = False,
    diagnostics: Optional[dict[str, Any]] = None,
) -> StrategyDecision:
    close_time = _bar_close_time(bar)
    signal_key = build_signal_key(action, close_time) if action else ""
    client_id = build_client_order_id(signal_key, action, close_time) if action else ""
    return StrategyDecision(
        action=action,
        signal_key=signal_key,
        client_order_id=client_id,
        bar_close_time=close_time,
        signal_price=float(bar.close),
        entry_low=entry_low,
        reason=reason,
        hm_detected=hm_detected,
        diagnostics=dict(diagnostics or {}),
    )


class Zec4hStrategy:
    """Closed-bar-only LONG strategy with no exchange side effects."""

    def initialize_baseline(self, bars: Sequence[MarketBar], state: StrategyState) -> None:
        if len(bars) < 28:
            raise ValueError("at least 28 closed bars are required")
        for bar in bars:
            _bar_close_time(bar)
        closes = [float(bar.close) for bar in bars]
        ma = _sma(closes, 27)
        dif, _dea = _macd_lines(closes)
        index = len(bars) - 1
        current_ma = ma[index]
        if current_ma is None:
            raise ValueError("SMA27 unavailable")
        state.buy_condition_active = closes[index] > current_ma and dif[index] > dif[index - 1]
        state.sell_condition_active = closes[index] < current_ma and dif[index] < dif[index - 1]
        state.last_processed_bar_close_time = _bar_close_time(bars[index])

    def evaluate(
        self,
        bars: Sequence[MarketBar],
        state: StrategyState,
        *,
        strategy_equity: float,
        actual_position_qty: Optional[float] = None,
    ) -> StrategyDecision:
        if len(bars) < 28:
            raise ValueError("at least 28 closed bars are required")
        for bar in bars[-28:]:
            _bar_close_time(bar)
        current = bars[-1]
        previous = bars[-2]
        close_time = _bar_close_time(current)
        qty = state.actual_position_qty if actual_position_qty is None else float(actual_position_qty)
        if qty < -1e-12:
            raise ValueError("negative exchange position is forbidden for LONG_ONLY")
        state.actual_position_qty = max(qty, 0.0)
        has_position = state.actual_position_qty > 1e-12

        # The 30 USDT capital floor is an account risk circuit-breaker, not a
        # trading signal.  It must remain active between 4H bar transitions.
        if strategy_equity <= HARD_EQUITY_FLOOR:
            state.target_reached = False
            state.hard_stop_reason = "STRATEGY_EQUITY_AT_OR_BELOW_30"
            if has_position:
                state.pending_action = LiveAction.HARD_STOP_CLOSE.value
                return _decision(
                    action=LiveAction.HARD_STOP_CLOSE.value,
                    bar=current,
                    reason=state.hard_stop_reason,
                )
            state.phase = StrategyPhase.HARD_STOP.value
            self._clear_scaling_state(state)
            return _decision(action=None, bar=current, reason="HARD_STOP")

        if state.last_processed_bar_close_time and close_time <= state.last_processed_bar_close_time:
            return _decision(action=None, bar=current, reason="BAR_ALREADY_PROCESSED")

        closes = [float(bar.close) for bar in bars]
        ma_values = _sma(closes, 27)
        dif_values, dea_values = _macd_lines(closes)
        ma = ma_values[-1]
        previous_ma = ma_values[-2]
        if ma is None or previous_ma is None:
            raise ValueError("SMA27 unavailable")
        buy_condition = current.close > ma and dif_values[-1] > dif_values[-2]
        sell_condition = current.close < ma and dif_values[-1] < dif_values[-2]
        buy_candidate = buy_condition and not state.buy_condition_active
        sell_candidate = sell_condition and not state.sell_condition_active
        hm_detected = _is_black_horse(bars[-3:])
        if hm_detected:
            state.last_hm_bar_close_time = close_time
            state.hm_observation_count += 1

        if state.last_signal:
            state.bars_since_signal += 1

        buy_signal = False
        if buy_candidate:
            buy_signal = not (
                state.last_signal == "SELL"
                and state.bars_since_signal <= 5
                and state.last_signal_open is not None
                and current.close <= state.last_signal_open
            )
            if buy_signal:
                state.last_signal = "BUY"
                state.last_signal_open = float(current.open)
                state.bars_since_signal = 0

        if sell_candidate:
            allowed_sell_marker = not (
                state.last_signal == "BUY"
                and state.bars_since_signal <= 5
                and state.last_signal_open is not None
                and current.close >= state.last_signal_open
            )
            if allowed_sell_marker:
                state.last_signal = "SELL"
                state.last_signal_open = float(current.open)
                state.bars_since_signal = 0

        state.buy_condition_active = bool(buy_condition)
        state.sell_condition_active = bool(sell_condition)
        state.last_processed_bar_close_time = close_time

        diagnostics = {
            "ma": ma,
            "previous_ma": previous_ma,
            "dif": dif_values[-1],
            "previous_dif": dif_values[-2],
            "dea": dea_values[-1],
            "buy_condition": buy_condition,
            "buy_candidate": buy_candidate,
            "buy_signal": buy_signal,
            "sell_marker": sell_candidate,
            "hm_detected": hm_detected,
        }

        if state.phase == StrategyPhase.HARD_STOP.value:
            if has_position:
                state.pending_action = LiveAction.HARD_STOP_CLOSE.value
                return _decision(
                    action=LiveAction.HARD_STOP_CLOSE.value,
                    bar=current,
                    reason=state.hard_stop_reason or "HARD_STOP_RECOVERY_CLOSE",
                    hm_detected=hm_detected,
                    diagnostics=diagnostics,
                )
            return _decision(
                action=None,
                bar=current,
                reason=state.hard_stop_reason or "HARD_STOP",
                hm_detected=hm_detected,
                diagnostics=diagnostics,
            )

        if strategy_equity >= TARGET_EQUITY:
            state.target_reached = True
            if not has_position:
                state.phase = StrategyPhase.TARGET_REACHED_PAUSED.value
                self._clear_scaling_state(state)

        # A completed-bar stop is always evaluated before reduce or re-add.
        if has_position and state.entry_low is not None and current.close < state.entry_low:
            state.pending_action = LiveAction.STOP_CLOSE.value
            return _decision(
                action=LiveAction.STOP_CLOSE.value,
                bar=current,
                reason="CLOSED_BAR_BELOW_ENTRY_LOW",
                hm_detected=hm_detected,
                diagnostics=diagnostics,
            )

        if state.wait_add_position and buy_signal:
            self._clear_readd_state(state)
            if has_position:
                state.phase = StrategyPhase.LONG_REDUCED.value

        if has_position and state.phase == StrategyPhase.LONG_FULL.value:
            reduce_reason = self._reduce_reason(bars, state)
            if reduce_reason:
                state.pending_action = LiveAction.REDUCE_50.value
                return _decision(
                    action=LiveAction.REDUCE_50.value,
                    bar=current,
                    reason=reduce_reason,
                    hm_detected=hm_detected,
                    diagnostics=diagnostics,
                )

        if has_position and state.wait_add_position and not state.target_reached:
            add_decision = self._evaluate_readd(
                bars=bars,
                state=state,
                ma=ma,
                previous_ma=previous_ma,
                buy_signal=buy_signal,
                diagnostics=diagnostics,
                hm_detected=hm_detected,
            )
            if add_decision is not None:
                return add_decision

        # Capture the newest attack candle only after stop/reduce decisions.
        if has_position and state.phase == StrategyPhase.LONG_FULL.value:
            window = bars[-20:]
            if current.close > current.open and current.close == max(item.close for item in window):
                state.attack_open = float(current.open)
                state.attack_close = float(current.close)
                state.attack_gain_rate = (current.close - current.open) / current.open
                state.attack_bar_close_time = close_time
                state.wait_attack_reduce = True

        if (
            buy_signal
            and not has_position
            and state.phase == StrategyPhase.FLAT.value
            and not state.target_reached
        ):
            state.pending_action = LiveAction.OPEN.value
            return _decision(
                action=LiveAction.OPEN.value,
                bar=current,
                entry_low=float(current.low),
                reason="BUY_FALSE_TO_TRUE",
                hm_detected=hm_detected,
                diagnostics=diagnostics,
            )

        reason = "HM_OBSERVATION_ONLY" if hm_detected else "NO_TRADE_ACTION"
        return _decision(action=None, bar=current, reason=reason, hm_detected=hm_detected, diagnostics=diagnostics)

    @staticmethod
    def _reduce_reason(bars: Sequence[MarketBar], state: StrategyState) -> str:
        if not state.wait_attack_reduce or state.attack_open is None or state.attack_gain_rate is None:
            return ""
        current, previous = bars[-1], bars[-2]
        rule_a = current.close < state.attack_open and previous.close >= state.attack_open
        bearish_body_rate = (current.open - current.close) / current.open if current.close < current.open else 0.0
        rule_b = (
            state.attack_gain_rate > 0.05
            and current.close < current.open
            and bearish_body_rate >= state.attack_gain_rate * 0.5
        )
        if rule_a:
            return "FIRST_CLOSE_BELOW_ATTACK_OPEN"
        if rule_b:
            return "STRONG_ATTACK_BEARISH_HALF_RETRACE"
        return ""

    def _evaluate_readd(
        self,
        *,
        bars: Sequence[MarketBar],
        state: StrategyState,
        ma: float,
        previous_ma: float,
        buy_signal: bool,
        diagnostics: dict[str, Any],
        hm_detected: bool,
    ) -> Optional[StrategyDecision]:
        current, previous = bars[-1], bars[-2]
        if buy_signal or current.close < ma * 0.98:
            self._clear_readd_state(state)
            state.phase = StrategyPhase.LONG_REDUCED.value
            return None

        touch = ma >= previous_ma and current.low <= ma * 1.01 and current.close >= ma * 0.99
        if touch and not state.pullback_seen:
            state.pullback_seen = True
            state.bars_after_touch = 0

        if state.pullback_seen:
            state.bars_after_touch += 1
            rebound = current.close > current.open and current.close > ma and current.close > previous.close
            if rebound and state.bars_after_touch <= 5:
                state.pending_action = LiveAction.ADD_50.value
                return _decision(
                    action=LiveAction.ADD_50.value,
                    bar=current,
                    entry_low=float(current.low),
                    reason="VALID_MA_PULLBACK_REBOUND",
                    hm_detected=hm_detected,
                    diagnostics={**diagnostics, "touch_ma": touch, "rebound_confirm": rebound},
                )
            if state.bars_after_touch >= 5:
                self._clear_readd_state(state)
                state.phase = StrategyPhase.LONG_REDUCED.value
        return None

    @staticmethod
    def _clear_readd_state(state: StrategyState) -> None:
        state.wait_add_position = False
        state.pullback_seen = False
        state.bars_after_touch = 0

    @classmethod
    def _clear_scaling_state(cls, state: StrategyState) -> None:
        state.attack_open = None
        state.attack_close = None
        state.attack_gain_rate = None
        state.attack_bar_close_time = None
        state.wait_attack_reduce = False
        cls._clear_readd_state(state)

    @classmethod
    def apply_filled_action(
        cls,
        state: StrategyState,
        decision: StrategyDecision,
        *,
        filled_qty: float,
    ) -> None:
        """Advance strategy state only after the exchange reports FILLED."""
        qty = float(filled_qty)
        if qty <= 0 or not decision.action:
            raise ValueError("a positive filled quantity and action are required")
        action = decision.action
        if action == LiveAction.OPEN.value:
            state.full_position_qty = qty
            state.actual_position_qty = qty
            state.reduced_qty = 0.0
            state.entry_low = float(decision.entry_low) if decision.entry_low is not None else None
            state.phase = StrategyPhase.LONG_FULL.value
        elif action == LiveAction.REDUCE_50.value:
            state.actual_position_qty = max(0.0, state.actual_position_qty - qty)
            state.reduced_qty = qty
            state.phase = StrategyPhase.WAITING_READD.value
            state.wait_add_position = True
            state.pullback_seen = False
            state.bars_after_touch = 0
            state.wait_attack_reduce = False
        elif action == LiveAction.ADD_50.value:
            state.actual_position_qty += qty
            state.full_position_qty = max(state.full_position_qty, state.actual_position_qty)
            state.reduced_qty = 0.0
            state.entry_low = float(decision.entry_low) if decision.entry_low is not None else state.entry_low
            state.phase = StrategyPhase.LONG_FULL.value
            cls._clear_scaling_state(state)
        elif action in {LiveAction.STOP_CLOSE.value, LiveAction.HARD_STOP_CLOSE.value}:
            state.actual_position_qty = 0.0
            state.full_position_qty = 0.0
            state.reduced_qty = 0.0
            state.entry_low = None
            cls._clear_scaling_state(state)
            if action == LiveAction.HARD_STOP_CLOSE.value:
                state.phase = StrategyPhase.HARD_STOP.value
            elif state.target_reached:
                state.phase = StrategyPhase.TARGET_REACHED_PAUSED.value
            else:
                state.phase = StrategyPhase.FLAT.value
        else:
            raise ValueError("unknown filled action")
        state.pending_action = ""


class LiveExecutionLedger:
    """Single append-only JSONL ledger, separate from every Shadow artifact."""

    def __init__(self, path: Path):
        self.path = path

    def append(self, record: dict[str, Any]) -> None:
        required = {"strategy_id", "signal_key", "bar_close_time", "action", "status", "recorded_at"}
        missing = sorted(key for key in required if record.get(key) in (None, ""))
        if missing:
            raise ValueError(f"live ledger missing fields: {','.join(missing)}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.chmod(self.path, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"invalid live ledger record at line {number}")
            rows.append(value)
        return rows

    def latest_by_signal_key(self, signal_key: str) -> Optional[dict[str, Any]]:
        for row in reversed(self.read()):
            if row.get("signal_key") == signal_key:
                return row
        return None


def build_live_scorecard(
    records: Iterable[dict[str, Any]],
    *,
    current_equity: float,
    current_position: Any,
    current_open_orders: Any,
    strategy_state: StrategyState,
) -> dict[str, Any]:
    """Calculate only from exchange-derived execution ledger values."""
    latest: dict[str, dict[str, Any]] = {}
    for row in records:
        key = str(row.get("signal_key", ""))
        if key:
            latest[key] = dict(row)
    ordered = sorted(latest.values(), key=lambda row: str(row.get("recorded_at", "")))
    fills = [row for row in ordered if float(row.get("filled_qty", 0.0) or 0.0) > 0]
    funding_rows = [row for row in ordered if row.get("status") == "ACCOUNT_INCOME"]
    trades: list[dict[str, float]] = []
    active: Optional[dict[str, float]] = None
    for row in ordered:
        action = row.get("action")
        has_execution = float(row.get("filled_qty", 0.0) or 0.0) > 0
        if has_execution and action == LiveAction.OPEN.value:
            if active is not None:
                raise ValueError("overlapping live trade sessions in execution ledger")
            active = {"gross": 0.0, "fees": 0.0, "funding": 0.0, "slippage": 0.0}
        if has_execution and active is not None:
            active["gross"] += float(row.get("realized_pnl", 0.0) or 0.0)
            active["fees"] += float(row.get("fee", 0.0) or 0.0)
            active["slippage"] += float(row.get("realized_slippage", 0.0) or 0.0)
        if row.get("status") == "ACCOUNT_INCOME" and active is not None:
            active["funding"] += float(row.get("funding", 0.0) or 0.0)
        if (
            has_execution
            and action in {LiveAction.STOP_CLOSE.value, LiveAction.HARD_STOP_CLOSE.value}
            and active is not None
        ):
            active["net"] = active["gross"] - active["fees"] + active["funding"]
            trades.append(active)
            active = None
    pnl = [item["gross"] for item in trades]
    net = [item["net"] for item in trades]
    gross_profit = sum(value for value in pnl if value > 0)
    gross_loss = abs(sum(value for value in pnl if value < 0))
    net_profit = float(current_equity) - STARTING_EQUITY
    wins = sum(value > 0 for value in net)
    losses = sum(value < 0 for value in net)
    equity_path = [STARTING_EQUITY]
    exit_rows = [
        row for row in fills
        if row.get("action") in {LiveAction.STOP_CLOSE.value, LiveAction.HARD_STOP_CLOSE.value}
    ]
    equity_path.extend(float(row.get("strategy_equity_after", equity_path[-1]) or equity_path[-1]) for row in exit_rows)
    peak = equity_path[0]
    max_drawdown = 0.0
    for value in equity_path:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, peak - value)
    net_gains = sum(value for value in net if value > 0)
    net_losses = abs(sum(value for value in net if value < 0))
    return {
        "strategy_id": STRATEGY_ID,
        "starting_equity": STARTING_EQUITY,
        "current_equity": float(current_equity),
        "net_profit": net_profit,
        "target_equity": TARGET_EQUITY,
        "target_remaining": max(0.0, TARGET_EQUITY - float(current_equity)),
        "closed_trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(trades) if trades else None,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "actual_fees": sum(float(row.get("fee", 0.0) or 0.0) for row in fills),
        "actual_funding": sum(float(row.get("funding", 0.0) or 0.0) for row in funding_rows),
        "actual_slippage": sum(float(row.get("realized_slippage", 0.0) or 0.0) for row in fills),
        "gross_profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "net_profit_factor": net_gains / net_losses if net_losses > 0 else None,
        "net_expectancy": sum(net) / len(net) if net else None,
        "maximum_drawdown": max_drawdown,
        "current_position": current_position,
        "current_open_orders": current_open_orders,
        "strategy_state": strategy_state.phase,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }


def safe_initial_notional(strategy_equity: float) -> float:
    if not math.isfinite(strategy_equity) or strategy_equity <= 0:
        return 0.0
    # Strategy equity is isolated from the rest of the account.  The 4% reserve
    # absorbs fees, funding and small price changes before market submission.
    return max(0.0, float(strategy_equity) * INITIAL_NOTIONAL_BUFFER)
