"""Deterministic ZECUSDT 4H small-live strategy and local audit artifacts.

The module contains no credential loading and performs no network calls.  It is
safe to exercise with fixtures.  Real account access belongs to the separately
guarded adapter in :mod:`core.zec_4h_live_execution`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
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
LIVE_CAPITAL_CAP_USDT = 50.0
MARGIN_PER_TRADE_RATE = 0.01
TARGET_INITIAL_MARGIN_USDT = LIVE_CAPITAL_CAP_USDT * MARGIN_PER_TRADE_RATE
FIXED_LEVERAGE = 50
TARGET_INITIAL_NOTIONAL_USDT = TARGET_INITIAL_MARGIN_USDT * FIXED_LEVERAGE
TARGET_EQUITY = 150.0
HARD_EQUITY_FLOOR = 30.0
WARMUP_BARS = 200
APPROVED_LIVE_SAFETY_DEVIATIONS = (
    "NO_REDUCTION_BELOW_HALF_TARGET",
    "CLEAR_ATTACK_STATE_ACROSS_POSITION_BOUNDARY",
)


class StrategyPhase(str, Enum):
    FLAT = "FLAT"
    LONG_FULL = "LONG_FULL"
    LONG_REDUCED = "LONG_REDUCED"
    WAITING_READD = "WAITING_READD"
    HARD_STOP = "HARD_STOP"
    TARGET_REACHED_PAUSED = "TARGET_REACHED_PAUSED"
    SAFETY_EXIT_REQUIRED = "SAFETY_EXIT_REQUIRED"
    RECOVERY_REDUCE_REQUIRED = "RECOVERY_REDUCE_REQUIRED"


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
    pending_decision: dict[str, Any] = field(default_factory=dict)
    target_reached: bool = False
    hard_stop_reason: str = ""
    last_hm_bar_close_time: Optional[str] = None
    hm_observation_count: int = 0
    warmup_complete: bool = False
    warmup_bar_count: int = 0
    recovery_status: str = ""
    recovery_decision: dict[str, Any] = field(default_factory=dict)
    applied_fill_signal_keys: list[str] = field(default_factory=list)
    stop_guard_active: bool = False
    stop_guard_price: Optional[float] = None

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


@dataclass(frozen=True)
class StateReplayResult:
    processed_bars: int
    evidence: tuple[dict[str, Any], ...]
    risk_reduction_decision: Optional[StrategyDecision]
    recovery_status: str
    desired_position_qty: float
    actual_position_qty: float


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
        if len(bars) < WARMUP_BARS:
            raise ValueError(f"at least {WARMUP_BARS} closed bars are required for warmup")
        for bar in bars:
            _bar_close_time(bar)
        closes = [float(bar.close) for bar in bars]
        ma_values = _sma(closes, 27)
        dif, _dea = _macd_lines(closes)
        state.last_signal = ""
        state.last_signal_open = None
        state.bars_since_signal = 0
        state.buy_condition_active = False
        state.sell_condition_active = False
        state.attack_open = None
        state.attack_close = None
        state.attack_gain_rate = None
        state.attack_bar_close_time = None
        state.wait_attack_reduce = False
        state.wait_add_position = False
        state.pullback_seen = False
        state.bars_after_touch = 0
        state.last_hm_bar_close_time = None
        state.hm_observation_count = 0

        for index, bar in enumerate(bars):
            close_time = _bar_close_time(bar)
            if index >= 2 and _is_black_horse(bars[index - 2 : index + 1]):
                state.last_hm_bar_close_time = close_time
                state.hm_observation_count += 1

            attack_condition = False
            if index >= 19:
                window = bars[index - 19 : index + 1]
                attack_condition = bar.close > bar.open and bar.close == max(item.close for item in window)
                if attack_condition:
                    state.attack_open = float(bar.open)
                    state.attack_close = float(bar.close)
                    state.attack_gain_rate = (bar.close - bar.open) / bar.open
                    state.attack_bar_close_time = close_time
                    state.wait_attack_reduce = True

            reduce_signal = False
            if (
                not attack_condition
                and index >= 1
                and state.wait_attack_reduce
                and state.attack_open is not None
                and state.attack_gain_rate is not None
            ):
                previous = bars[index - 1]
                rule_a = bar.close < state.attack_open and previous.close >= state.attack_open
                bearish_rate = (bar.open - bar.close) / bar.open if bar.close < bar.open else 0.0
                rule_b = (
                    state.attack_gain_rate > 0.05
                    and bar.close < bar.open
                    and bearish_rate >= state.attack_gain_rate * 0.5
                )
                if rule_a or rule_b:
                    reduce_signal = True
                    state.wait_attack_reduce = False
                    state.wait_add_position = True
                    state.pullback_seen = False
                    state.bars_after_touch = 0

            current_ma = ma_values[index]
            buy_signal = False
            if current_ma is not None and index >= 1:
                buy_condition = bar.close > current_ma and dif[index] > dif[index - 1]
                sell_condition = bar.close < current_ma and dif[index] < dif[index - 1]
                buy_candidate = buy_condition and not state.buy_condition_active
                sell_candidate = sell_condition and not state.sell_condition_active
                if state.last_signal:
                    state.bars_since_signal += 1
                if buy_candidate and state.last_signal != "BUY":
                    allowed = not (
                        state.last_signal == "SELL"
                        and state.bars_since_signal <= 5
                        and state.last_signal_open is not None
                        and bar.close <= state.last_signal_open
                    )
                    if allowed:
                        buy_signal = True
                        state.last_signal = "BUY"
                        state.last_signal_open = float(bar.open)
                        state.bars_since_signal = 0
                if sell_candidate and state.last_signal != "SELL":
                    allowed = not (
                        state.last_signal == "BUY"
                        and state.bars_since_signal <= 5
                        and state.last_signal_open is not None
                        and bar.close >= state.last_signal_open
                    )
                    if allowed:
                        state.last_signal = "SELL"
                        state.last_signal_open = float(bar.open)
                        state.bars_since_signal = 0
                state.buy_condition_active = bool(buy_condition)
                state.sell_condition_active = bool(sell_condition)

                if state.wait_add_position and not reduce_signal:
                    previous_ma = ma_values[index - 1]
                    if buy_signal or bar.close < current_ma * 0.98:
                        self._clear_readd_state(state)
                    elif previous_ma is not None:
                        touch = (
                            current_ma >= previous_ma
                            and bar.low <= current_ma * 1.01
                            and bar.close >= current_ma * 0.99
                        )
                        if touch:
                            state.pullback_seen = True
                            state.bars_after_touch = 0
                        rebound = (
                            state.pullback_seen
                            and bar.close > bar.open
                            and bar.close > current_ma
                            and bar.close > bars[index - 1].close
                        )
                        if rebound and state.bars_after_touch <= 5:
                            self._clear_readd_state(state)
                        elif state.pullback_seen:
                            state.bars_after_touch += 1
                            if state.bars_after_touch > 5:
                                state.pullback_seen = False
                                state.bars_after_touch = 0
            state.last_processed_bar_close_time = close_time

        state.phase = StrategyPhase.FLAT.value
        state.pending_action = ""
        state.entry_low = None
        state.actual_position_qty = 0.0
        state.full_position_qty = 0.0
        state.reduced_qty = 0.0
        state.warmup_complete = True
        state.warmup_bar_count = len(bars)

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

        if state.last_processed_bar_close_time and close_time <= state.last_processed_bar_close_time:
            # The capital floor remains active between 4H transitions.  No
            # technical state is reprocessed for an already-consumed bar.
            if strategy_equity <= HARD_EQUITY_FLOOR:
                return self._hard_floor_decision(state, current, has_position)
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
        if buy_candidate and state.last_signal != "BUY":
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

        sell_signal = False
        if sell_candidate and state.last_signal != "SELL":
            allowed_sell_marker = not (
                state.last_signal == "BUY"
                and state.bars_since_signal <= 5
                and state.last_signal_open is not None
                and current.close >= state.last_signal_open
            )
            if allowed_sell_marker:
                sell_signal = True
                state.last_signal = "SELL"
                state.last_signal_open = float(current.open)
                state.bars_since_signal = 0

        state.buy_condition_active = bool(buy_condition)
        state.sell_condition_active = bool(sell_condition)
        state.last_processed_bar_close_time = close_time

        window = bars[-20:]
        attack_condition = current.close > current.open and current.close == max(item.close for item in window)
        if attack_condition:
            state.attack_open = float(current.open)
            state.attack_close = float(current.close)
            state.attack_gain_rate = (current.close - current.open) / current.open
            state.attack_bar_close_time = close_time
            state.wait_attack_reduce = True

        diagnostics = {
            "ma": ma,
            "previous_ma": previous_ma,
            "dif": dif_values[-1],
            "previous_dif": dif_values[-2],
            "dea": dea_values[-1],
            "buy_condition": buy_condition,
            "buy_candidate": buy_candidate,
            "buy_signal": buy_signal,
            "sell_candidate": sell_candidate,
            "sell_signal": sell_signal,
            "hm_detected": hm_detected,
            "attack_condition": attack_condition,
        }

        if strategy_equity <= HARD_EQUITY_FLOOR:
            return self._hard_floor_decision(
                state,
                current,
                has_position,
                hm_detected=hm_detected,
                diagnostics=diagnostics,
            )

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

        reduce_reason = "" if attack_condition else self._reduce_reason(bars, state)
        if reduce_reason:
            # This is the AiCoin source signal transition.  It is preserved in
            # every phase even when the live exposure guard blocks an order.
            state.wait_attack_reduce = False
            state.wait_add_position = True
            state.pullback_seen = False
            state.bars_after_touch = 0
            half_target = state.full_position_qty * 0.5
            reduce_order_allowed = (
                has_position
                and state.full_position_qty > 1e-12
                and state.actual_position_qty > half_target + 1e-12
            )
            diagnostics = {
                **diagnostics,
                "source_reduce_signal": True,
                "live_safety_deviation": "NO_REDUCTION_BELOW_HALF_TARGET",
                "reduce_order_allowed": reduce_order_allowed,
            }
            if reduce_order_allowed:
                state.pending_action = LiveAction.REDUCE_50.value
                return _decision(
                    action=LiveAction.REDUCE_50.value,
                    bar=current,
                    reason=reduce_reason,
                    hm_detected=hm_detected,
                    diagnostics=diagnostics,
                )
            return _decision(
                action=None,
                bar=current,
                reason="REDUCE_SIGNAL_BLOCKED_HALF_TARGET" if has_position else "REDUCE_SIGNAL_OBSERVED_FLAT",
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
        if touch:
            state.pullback_seen = True
            state.bars_after_touch = 0

        if state.pullback_seen:
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
            state.bars_after_touch += 1
            if state.bars_after_touch > 5:
                state.pullback_seen = False
                state.bars_after_touch = 0
        return None

    @classmethod
    def _hard_floor_decision(
        cls,
        state: StrategyState,
        current: MarketBar,
        has_position: bool,
        *,
        hm_detected: bool = False,
        diagnostics: Optional[dict[str, Any]] = None,
    ) -> StrategyDecision:
        state.target_reached = False
        state.hard_stop_reason = "STRATEGY_EQUITY_AT_OR_BELOW_30"
        if has_position:
            state.pending_action = LiveAction.HARD_STOP_CLOSE.value
            return _decision(
                action=LiveAction.HARD_STOP_CLOSE.value,
                bar=current,
                reason=state.hard_stop_reason,
                hm_detected=hm_detected,
                diagnostics=diagnostics,
            )
        state.phase = StrategyPhase.HARD_STOP.value
        cls._clear_scaling_state(state)
        return _decision(
            action=None,
            bar=current,
            reason="HARD_STOP",
            hm_detected=hm_detected,
            diagnostics=diagnostics,
        )

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
        record_applied_fill: bool = True,
    ) -> None:
        """Advance strategy state only after the exchange reports FILLED."""
        qty = float(filled_qty)
        if qty <= 0 or not decision.action:
            raise ValueError("a positive filled quantity and action are required")
        if record_applied_fill and decision.signal_key in state.applied_fill_signal_keys:
            return
        action = decision.action
        if action == LiveAction.OPEN.value:
            state.full_position_qty = qty
            state.actual_position_qty = qty
            state.reduced_qty = 0.0
            state.entry_low = float(decision.entry_low) if decision.entry_low is not None else None
            state.stop_guard_price = state.entry_low
            state.stop_guard_active = state.entry_low is not None and state.entry_low > 0
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
            state.stop_guard_price = state.entry_low
            state.stop_guard_active = state.entry_low is not None and state.entry_low > 0
            state.phase = StrategyPhase.LONG_FULL.value
            # AiCoin keeps the newest attack reference across an ADD.  Only a
            # confirmed full position close uses the approved boundary clear.
            cls._clear_readd_state(state)
        elif action in {LiveAction.STOP_CLOSE.value, LiveAction.HARD_STOP_CLOSE.value}:
            state.actual_position_qty = 0.0
            state.full_position_qty = 0.0
            state.reduced_qty = 0.0
            state.entry_low = None
            state.stop_guard_active = False
            state.stop_guard_price = None
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
        state.pending_decision = {}
        state.recovery_status = ""
        state.recovery_decision = {}
        if record_applied_fill:
            state.applied_fill_signal_keys.append(decision.signal_key)


def replay_missed_closed_bars(
    bars: Sequence[MarketBar],
    state: StrategyState,
    *,
    strategy_equity: float,
    actual_position_qty: float,
) -> StateReplayResult:
    """Replay two or more stale closed bars without increasing live risk.

    A projected state follows every AiCoin bar transition.  Only after that
    projection is complete is it compared with the exchange position.  Stale
    entries and adds are evidence-only; a stale stop or reduce may return one
    idempotent risk-reduction decision for the caller to reconcile and execute.
    """
    if len(bars) < WARMUP_BARS:
        raise ValueError(f"at least {WARMUP_BARS} closed bars are required for replay")
    for bar in bars:
        _bar_close_time(bar)
    if not state.last_processed_bar_close_time:
        raise ValueError("replay requires a prior processed bar boundary")
    unprocessed = [
        index for index, bar in enumerate(bars)
        if _bar_close_time(bar) > state.last_processed_bar_close_time
    ]
    if len(unprocessed) < 2:
        raise ValueError("state replay is reserved for two or more missed bars")
    boundary = datetime.fromisoformat(state.last_processed_bar_close_time.replace("Z", "+00:00"))
    expected = boundary + timedelta(hours=4)
    for index in unprocessed:
        observed = bars[index].close_time
        if observed is None or abs((observed - expected).total_seconds()) > 0.002:
            raise ValueError("closed-bar replay gap detected")
        expected = observed + timedelta(hours=4)

    actual_qty = max(0.0, float(actual_position_qty))
    projected = StrategyState.from_dict(state.to_dict())
    projected.actual_position_qty = actual_qty
    if actual_qty > 1e-12 and projected.full_position_qty <= 1e-12:
        raise ValueError("cannot replay an exchange position without a full-position target")

    strategy = Zec4hStrategy()
    evidence: list[dict[str, Any]] = []
    last_reduce: Optional[StrategyDecision] = None
    last_stop: Optional[StrategyDecision] = None
    stale_entry = False
    stale_add = False

    for index in unprocessed:
        decision = strategy.evaluate(
            bars[: index + 1],
            projected,
            strategy_equity=strategy_equity,
        )
        if decision.diagnostics.get("source_reduce_signal") and not decision.action:
            evidence.append({
                "status": "LIVE_SAFETY_DEVIATION_BLOCKED",
                "action": "REDUCE_50_SIGNAL",
                "signal_key": build_signal_key("REDUCE_50_SIGNAL", decision.bar_close_time),
                "bar_close_time": decision.bar_close_time,
                "reason": decision.reason,
                "live_safety_deviation": "NO_REDUCTION_BELOW_HALF_TARGET",
            })
        if decision.action == LiveAction.OPEN.value:
            stale_entry = True
            projected.pending_action = ""
            evidence.append({
                "status": "MISSED_STALE_ENTRY",
                "action": decision.action,
                "signal_key": decision.signal_key,
                "bar_close_time": decision.bar_close_time,
                "reason": "STALE_RISK_INCREASE_BLOCKED",
            })
        elif decision.action == LiveAction.ADD_50.value:
            stale_add = True
            add_qty = min(
                max(projected.reduced_qty, 0.0),
                max(projected.full_position_qty - projected.actual_position_qty, 0.0),
            )
            if add_qty > 1e-12:
                Zec4hStrategy.apply_filled_action(
                    projected,
                    decision,
                    filled_qty=add_qty,
                    record_applied_fill=False,
                )
            else:
                projected.pending_action = ""
            evidence.append({
                "status": "STALE_ADD_BLOCKED",
                "action": decision.action,
                "signal_key": decision.signal_key,
                "bar_close_time": decision.bar_close_time,
                "reason": "STALE_RISK_INCREASE_BLOCKED",
            })
        elif decision.action == LiveAction.REDUCE_50.value:
            reduce_qty = projected.actual_position_qty * 0.5
            if reduce_qty > 1e-12:
                Zec4hStrategy.apply_filled_action(
                    projected,
                    decision,
                    filled_qty=reduce_qty,
                    record_applied_fill=False,
                )
                last_reduce = decision
            evidence.append({
                "status": "MISSED_RISK_REDUCTION",
                "action": decision.action,
                "signal_key": decision.signal_key,
                "bar_close_time": decision.bar_close_time,
                "reason": decision.reason,
            })
        elif decision.action in {LiveAction.STOP_CLOSE.value, LiveAction.HARD_STOP_CLOSE.value}:
            close_qty = projected.actual_position_qty
            if close_qty > 1e-12:
                Zec4hStrategy.apply_filled_action(
                    projected,
                    decision,
                    filled_qty=close_qty,
                    record_applied_fill=False,
                )
                last_stop = decision
            evidence.append({
                "status": "MISSED_STOP_CLOSE",
                "action": decision.action,
                "signal_key": decision.signal_key,
                "bar_close_time": decision.bar_close_time,
                "reason": decision.reason,
            })

    desired_qty = max(0.0, projected.actual_position_qty)
    for name in StrategyState.__dataclass_fields__:
        setattr(state, name, getattr(projected, name))
    state.actual_position_qty = actual_qty
    state.pending_action = ""

    risk_decision: Optional[StrategyDecision] = None
    recovery_status = "STATE_REPLAY_COMPLETE"
    if actual_qty > desired_qty + 1e-12:
        if desired_qty <= 1e-12 and last_stop is not None:
            recovery_status = "SAFETY_EXIT_REQUIRED"
            state.phase = StrategyPhase.SAFETY_EXIT_REQUIRED.value
            state.pending_action = last_stop.action or LiveAction.STOP_CLOSE.value
            risk_decision = last_stop
        elif last_reduce is not None:
            recovery_status = "CONTROLLED_REDUCE_REQUIRED"
            state.phase = StrategyPhase.RECOVERY_REDUCE_REQUIRED.value
            state.pending_action = LiveAction.REDUCE_50.value
            risk_decision = last_reduce
    elif actual_qty + 1e-12 < desired_qty:
        if actual_qty <= 1e-12:
            recovery_status = "MISSED_STALE_ENTRY" if stale_entry else "STALE_RISK_INCREASE_BLOCKED"
            state.phase = StrategyPhase.FLAT.value
            state.full_position_qty = 0.0
            state.reduced_qty = 0.0
            state.entry_low = None
        else:
            recovery_status = "STALE_ADD_BLOCKED" if stale_add else "STALE_RISK_INCREASE_BLOCKED"
            state.phase = StrategyPhase.LONG_REDUCED.value
            state.reduced_qty = max(state.full_position_qty - actual_qty, 0.0)
        state.wait_add_position = False
        state.pullback_seen = False
        state.bars_after_touch = 0
    elif stale_entry:
        recovery_status = "MISSED_STALE_ENTRY"
    state.recovery_status = recovery_status
    state.recovery_decision = asdict(risk_decision) if risk_decision is not None else {}
    return StateReplayResult(
        processed_bars=len(unprocessed),
        evidence=tuple(evidence),
        risk_reduction_decision=risk_decision,
        recovery_status=recovery_status,
        desired_position_qty=desired_qty,
        actual_position_qty=actual_qty,
    )


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
        "live_capital_cap_usdt": LIVE_CAPITAL_CAP_USDT,
        "margin_per_trade_rate": MARGIN_PER_TRADE_RATE,
        "target_initial_margin_usdt": TARGET_INITIAL_MARGIN_USDT,
        "leverage_mode": "FIXED",
        "leverage": FIXED_LEVERAGE,
        "target_initial_notional_usdt": TARGET_INITIAL_NOTIONAL_USDT,
        "managed_capital_usdt": min(max(float(current_equity), 0.0), LIVE_CAPITAL_CAP_USDT),
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
        "recovery_status": strategy_state.recovery_status,
        "macd_numeric_parity": "STANDARD_EMA_AFTER_200_BAR_WARMUP",
        "warmup_bars": WARMUP_BARS,
        "live_safety_deviations": list(APPROVED_LIVE_SAFETY_DEVIATIONS),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }


def safe_initial_notional(strategy_equity: float, leverage: int) -> float:
    """Return the fixed-margin initial notional without exceeding the 50 USDT pool.

    ``strategy_equity`` is deliberately not allowed to scale the order.  It is
    accepted only so callers can fail closed when the strategy has no valid
    capital evidence.  The live contract allocates exactly one percent of the
    fixed 50 USDT pool as initial margin and lets the exchange/account-specific
    leverage determine notional exposure.
    """
    if not math.isfinite(strategy_equity) or strategy_equity <= 0:
        return 0.0
    if not isinstance(leverage, int) or isinstance(leverage, bool) or leverage <= 0:
        return 0.0
    managed_capital = min(float(strategy_equity), LIVE_CAPITAL_CAP_USDT)
    if managed_capital < TARGET_INITIAL_MARGIN_USDT:
        return 0.0
    return TARGET_INITIAL_MARGIN_USDT * leverage
