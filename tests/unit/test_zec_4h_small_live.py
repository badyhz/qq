from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import scripts.run_zec_4h_small_live as live_runner

from core.paper_trading.data_source import MarketBar
from core.zec_4h_live import (
    APPROVED_LIVE_SAFETY_DEVIATIONS,
    LiveAction,
    LiveExecutionLedger,
    StrategyDecision,
    StrategyPhase,
    StrategyState,
    Zec4hStrategy,
    WARMUP_BARS,
    LIVE_CAPITAL_CAP_USDT,
    TARGET_INITIAL_MARGIN_USDT,
    build_live_scorecard,
    load_strategy_state,
    save_strategy_state,
    replay_missed_closed_bars,
)
from core.zec_4h_live_execution import (
    BinanceUsdMExecutionAdapter,
    LiveExecutionEngine,
    UNKNOWN_STATUS,
    extract_symbol_rules,
    reconcile_startup,
    resolve_max_allowed_leverage,
    recover_unapplied_filled_transitions,
    run_live_preflight,
    strategy_equity_from_evidence,
    verify_dedicated_account_boundary,
)
from scripts.run_zec_4h_small_live import (
    _decision_from_record,
    _execute_with_immediate_safety_exit,
    _recover_persisted_recovery_outcome,
)


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)
RULES = {
    "tick_size": 0.01,
    "step_size": 0.001,
    "min_qty": 0.001,
    "min_notional": 5.0,
    "price_precision": 2,
    "qty_precision": 3,
}


def bars_from_closes(
    closes: list[float],
    *,
    opens: list[float] | None = None,
    lows: list[float] | None = None,
    highs: list[float] | None = None,
    volumes: list[float] | None = None,
    start_index: int = 0,
) -> list[MarketBar]:
    rows = []
    for i, close in enumerate(closes):
        opened = opens[i] if opens else close - 0.2
        low = lows[i] if lows else min(opened, close) - 0.5
        high = highs[i] if highs else max(opened, close) + 0.5
        opened_at = BASE + timedelta(hours=4 * (i + start_index))
        rows.append(MarketBar(
            timestamp=opened_at.timestamp(),
            open=opened,
            high=high,
            low=low,
            close=close,
            volume=(volumes[i] if volumes else 100.0 + i),
            symbol="ZECUSDT",
            timeframe="4h",
            close_time=opened_at + timedelta(hours=4) - timedelta(milliseconds=1),
            provider_closed=True,
        ))
    return rows


def rising_signal_bars() -> list[MarketBar]:
    return bars_from_closes([100.0] * 27 + [106.0])


def state_before_latest(**overrides) -> StrategyState:
    bars = rising_signal_bars()
    values = {
        "last_processed_bar_close_time": bars[-2].close_time.isoformat(timespec="milliseconds"),
        "buy_condition_active": False,
        "sell_condition_active": False,
    }
    values.update(overrides)
    return StrategyState(**values)


def decision(action: str, *, entry_low: float | None = 90.0) -> StrategyDecision:
    close_time = "2026-08-24T16:00:00.000+00:00"
    return StrategyDecision(
        action=action,
        signal_key=f"zec_4h_live_v1:ZECUSDT:4h:20260824T160000Z:{action}",
        client_order_id=f"z4-{action.lower()}",
        bar_close_time=close_time,
        signal_price=100.0,
        entry_low=entry_low,
        reason="TEST",
    )


class FakeAdapter:
    def __init__(self):
        self.submit_count = 0
        self.submit_response = {
            "status": "FILLED", "executedQty": "0.375", "avgPrice": "100",
            "orderId": "1001", "clientOrderId": "fake",
        }
        self.submit_error: Exception | None = None
        self.submit_responses = []
        self.query_response = None
        self.position = {"symbol": "ZECUSDT", "positionAmt": "0", "isolated": True, "leverage": "75"}
        self.open_orders = []
        self.account = {
            "canTrade": True,
            "totalMarginBalance": "50",
            "totalWalletBalance": "50",
            "totalUnrealizedProfit": "0",
        }
        self.available_balance = 50.0
        self.fills = []
        self.income = []
        self.submitted = []
        self.dual_side_position = False

    def get_account(self): return dict(self.account)
    def get_balance(self):
        return [{
            "asset": "USDT",
            "balance": str(self.available_balance),
            "availableBalance": str(self.available_balance),
        }]
    def get_position(self, symbol="ZECUSDT"): return dict(self.position)
    def get_open_orders(self, symbol="ZECUSDT"): return [dict(row) for row in self.open_orders]
    def get_exchange_info(self): return exchange_info_fixture()
    def get_server_time(self): return {"serverTime": int(BASE.timestamp() * 1000)}
    def get_position_mode(self): return {"dualSidePosition": self.dual_side_position}
    def get_api_restrictions(self):
        return {"enableFutures": True, "enableWithdrawals": False, "ipRestrict": True}
    def get_leverage_brackets(self, symbol="ZECUSDT"):
        return [{
            "symbol": symbol,
            "brackets": [
                {"bracket": 1, "initialLeverage": 75, "notionalFloor": 0, "notionalCap": 10000},
                {"bracket": 2, "initialLeverage": 50, "notionalFloor": 10000, "notionalCap": 50000},
            ],
        }]
    def get_symbol_config(self, symbol="ZECUSDT"):
        return {
            "symbol": symbol,
            "marginType": "ISOLATED" if self.position.get("isolated") else "CROSSED",
            "leverage": int(float(self.position.get("leverage", 0) or 0)),
            "maxNotionalValue": "10000",
        }
    def set_leverage(self, leverage, symbol="ZECUSDT"):
        self.position["leverage"] = str(leverage)
        return {"leverage": leverage, "symbol": symbol}
    def set_margin_type(self, margin_type, symbol="ZECUSDT"):
        self.position["isolated"] = str(margin_type).upper() == "ISOLATED"
        self.position["marginType"] = str(margin_type).lower()
        return {"code": 200}

    def submit_market_order(self, **kwargs):
        self.submit_count += 1
        self.submitted.append(dict(kwargs))
        if self.submit_error:
            raise self.submit_error
        row = dict(self.submit_responses.pop(0) if self.submit_responses else self.submit_response)
        row["clientOrderId"] = kwargs["client_order_id"]
        filled_qty = float(row.get("executedQty", 0.0) or 0.0)
        if filled_qty > 0:
            current_qty = float(self.position.get("positionAmt", 0.0) or 0.0)
            if kwargs["side"] == "BUY":
                current_qty += filled_qty
            else:
                current_qty = max(0.0, current_qty - filled_qty)
            self.position["positionAmt"] = str(current_qty)
        return row

    def query_order(self, **kwargs): return None if self.query_response is None else dict(self.query_response)
    def cancel_order(self, **kwargs): return {"status": "CANCELED"}
    def get_fills(self, symbol="ZECUSDT", order_id=""): return [dict(row) for row in self.fills]
    def get_income(self, symbol="ZECUSDT", income_type="FUNDING_FEE"): return [dict(row) for row in self.income]


def exchange_info_fixture():
    return {
        "symbols": [{
            "symbol": "ZECUSDT",
            "status": "TRADING",
            "contractType": "PERPETUAL",
            "pricePrecision": 2,
            "quantityPrecision": 3,
            "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                {"filterType": "MARKET_LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
                {"filterType": "MIN_NOTIONAL", "notional": "5"},
            ],
        }]
    }


def test_buy_is_false_to_true_only_and_same_bar_is_idempotent():
    state = state_before_latest()
    strategy = Zec4hStrategy()
    first = strategy.evaluate(rising_signal_bars(), state, strategy_equity=50)
    second = strategy.evaluate(rising_signal_bars(), state, strategy_equity=50)
    assert first.action == LiveAction.OPEN.value
    assert second.action is None
    assert second.reason == "BAR_ALREADY_PROCESSED"


def test_five_bar_reverse_noise_filter_blocks_buy():
    state = state_before_latest(last_signal="SELL", last_signal_open=110.0, bars_since_signal=2)
    result = Zec4hStrategy().evaluate(rising_signal_bars(), state, strategy_equity=50)
    assert result.action is None
    assert state.last_signal == "SELL"


def test_occupied_position_blocks_normal_buy():
    state = state_before_latest(phase=StrategyPhase.LONG_FULL.value, actual_position_qty=1.0, entry_low=80.0)
    result = Zec4hStrategy().evaluate(rising_signal_bars(), state, strategy_equity=50)
    assert result.action is None


def test_sell_marker_never_closes_or_opens_short():
    bars = bars_from_closes([100.0] * 27 + [94.0])
    state = full_long_state(bars, entry_low=80.0, sell_condition_active=False)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action is None
    assert state.last_signal == "SELL"
    assert state.phase == StrategyPhase.LONG_FULL.value


def test_black_horse_is_observation_only():
    closes = [90.0] * 25 + [91.0, 94.0, 100.0]
    opens = [89.8] * 25 + [90.0, 91.5, 95.0]
    lows = [89.0] * 25 + [89.5, 91.0, 94.0]
    highs = [91.0] * 25 + [91.2, 94.2, 100.2]
    volumes = [100.0] * 25 + [100.0, 150.0, 200.0]
    bars = bars_from_closes(closes, opens=opens, lows=lows, highs=highs, volumes=volumes)
    state = StrategyState(
        last_processed_bar_close_time=bars[-2].close_time.isoformat(timespec="milliseconds"),
        buy_condition_active=True,
    )
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.hm_detected is True
    assert result.action is None
    assert state.hm_observation_count == 1
    assert state.last_hm_bar_close_time == result.bar_close_time


def full_long_state(bars: list[MarketBar], **overrides) -> StrategyState:
    values = dict(
        phase=StrategyPhase.LONG_FULL.value,
        actual_position_qty=1.0,
        full_position_qty=1.0,
        entry_low=70.0,
        last_processed_bar_close_time=bars[-2].close_time.isoformat(timespec="milliseconds"),
        buy_condition_active=True,
    )
    values.update(overrides)
    return StrategyState(**values)


def test_reduce_rule_a_first_close_below_attack_open():
    bars = bars_from_closes([100.0] * 26 + [101.0, 99.0])
    state = full_long_state(
        bars, attack_open=100.0, attack_close=104.0, attack_gain_rate=0.04,
        wait_attack_reduce=True,
    )
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action == LiveAction.REDUCE_50.value
    assert result.reason == "FIRST_CLOSE_BELOW_ATTACK_OPEN"


def test_reduce_rule_b_strong_bearish_half_retrace():
    closes = [100.0] * 27 + [104.0]
    opens = [99.8] * 27 + [110.0]
    bars = bars_from_closes(closes, opens=opens)
    state = full_long_state(
        bars, attack_open=90.0, attack_close=99.0, attack_gain_rate=0.10,
        wait_attack_reduce=True,
    )
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action == LiveAction.REDUCE_50.value
    assert result.reason == "STRONG_ATTACK_BEARISH_HALF_RETRACE"


def test_reduce_fill_transitions_once_to_waiting_readd():
    state = StrategyState(
        phase=StrategyPhase.LONG_FULL.value,
        actual_position_qty=1,
        full_position_qty=1,
        entry_low=80.0,
    )
    Zec4hStrategy.apply_filled_action(state, decision(LiveAction.REDUCE_50.value), filled_qty=0.5)
    assert state.phase == StrategyPhase.WAITING_READD.value
    assert state.wait_add_position is True
    assert state.actual_position_qty == pytest.approx(0.5)
    assert state.wait_attack_reduce is False


@pytest.mark.parametrize("phase,qty", [
    (StrategyPhase.FLAT.value, 0.0),
    (StrategyPhase.LONG_FULL.value, 1.0),
    (StrategyPhase.LONG_REDUCED.value, 0.5),
    (StrategyPhase.WAITING_READD.value, 0.5),
])
def test_attack_reference_updates_in_every_strategy_phase(phase, qty):
    bars = rising_signal_bars()
    state = state_before_latest(
        phase=phase,
        actual_position_qty=qty,
        full_position_qty=1.0 if qty else 0.0,
        reduced_qty=0.5 if qty == 0.5 else 0.0,
        entry_low=80.0 if qty else None,
        last_signal="BUY",
        buy_condition_active=True,
    )
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action is None
    assert state.attack_open == pytest.approx(bars[-1].open)
    assert state.attack_close == pytest.approx(bars[-1].close)
    assert state.wait_attack_reduce is True


def test_second_reduce_signal_at_half_is_recorded_but_has_no_order():
    bars = bars_from_closes([100.0] * 26 + [101.0, 99.0])
    state = StrategyState(
        phase=StrategyPhase.WAITING_READD.value,
        actual_position_qty=0.5,
        full_position_qty=1.0,
        reduced_qty=0.5,
        entry_low=80.0,
        last_processed_bar_close_time=bars[-2].close_time.isoformat(timespec="milliseconds"),
        buy_condition_active=True,
        attack_open=100.0,
        attack_close=104.0,
        attack_gain_rate=0.04,
        wait_attack_reduce=True,
    )
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action is None
    assert result.reason == "REDUCE_SIGNAL_BLOCKED_HALF_TARGET"
    assert result.diagnostics["source_reduce_signal"] is True
    assert result.diagnostics["live_safety_deviation"] == "NO_REDUCTION_BELOW_HALF_TARGET"
    assert state.wait_add_position is True
    assert state.wait_attack_reduce is False
    assert state.actual_position_qty == pytest.approx(0.5)


def test_add_to_full_reenables_a_later_attack_reduce_cycle():
    state = StrategyState(
        phase=StrategyPhase.WAITING_READD.value,
        actual_position_qty=0.5,
        full_position_qty=1.0,
        reduced_qty=0.5,
        entry_low=80.0,
    )
    Zec4hStrategy.apply_filled_action(
        state,
        decision(LiveAction.ADD_50.value, entry_low=95.0),
        filled_qty=0.5,
    )
    assert state.phase == StrategyPhase.LONG_FULL.value

    attack_bars = rising_signal_bars()
    state.last_processed_bar_close_time = attack_bars[-2].close_time.isoformat(timespec="milliseconds")
    state.buy_condition_active = True
    state.last_signal = "BUY"
    assert Zec4hStrategy().evaluate(attack_bars, state, strategy_equity=50).action is None
    attack_open = state.attack_open

    break_bars = bars_from_closes(
        [110.0] * 26 + [110.0, attack_open - 1.0],
        start_index=28,
    )
    state.last_processed_bar_close_time = break_bars[-2].close_time.isoformat(timespec="milliseconds")
    result = Zec4hStrategy().evaluate(break_bars, state, strategy_equity=50)
    assert result.action == LiveAction.REDUCE_50.value


def readd_bars(*, current_close=101.0, current_open=100.2, current_low=99.8):
    closes = [100.0] * 27 + [current_close]
    opens = [99.8] * 27 + [current_open]
    lows = [99.0] * 27 + [current_low]
    return bars_from_closes(closes, opens=opens, lows=lows)


def waiting_state(bars, **overrides):
    values = dict(
        phase=StrategyPhase.WAITING_READD.value,
        actual_position_qty=0.5,
        full_position_qty=1.0,
        reduced_qty=0.5,
        entry_low=80.0,
        wait_add_position=True,
        last_processed_bar_close_time=bars[-2].close_time.isoformat(timespec="milliseconds"),
        buy_condition_active=True,
    )
    values.update(overrides)
    return StrategyState(**values)


def test_add_after_valid_ma_pullback_and_rebound():
    bars = readd_bars()
    state = waiting_state(bars)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action == LiveAction.ADD_50.value
    assert result.entry_low == pytest.approx(99.8)


def test_retouch_resets_window_and_timeout_keeps_waiting():
    bars = readd_bars(current_close=100.0, current_open=100.2, current_low=99.9)
    state = waiting_state(bars, pullback_seen=True, bars_after_touch=4)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action is None
    assert state.wait_add_position is True
    assert state.pullback_seen is True
    # Source resets to zero on touch, then increments after no same-bar add.
    assert state.bars_after_touch == 1


def test_ma_breakdown_cancels_add_wait():
    bars = readd_bars(current_close=97.0, current_open=98.0, current_low=96.5)
    state = waiting_state(bars)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action is None
    assert state.wait_add_position is False


def test_new_buy_signal_cancels_add_wait_without_adding():
    bars = rising_signal_bars()
    state = waiting_state(bars, buy_condition_active=False)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action is None
    assert state.wait_add_position is False


def test_same_direction_buy_edge_after_stop_stays_flat_until_valid_sell():
    strategy = Zec4hStrategy()
    state = state_before_latest(last_signal="BUY", last_signal_open=99.0, bars_since_signal=9)
    result = strategy.evaluate(rising_signal_bars(), state, strategy_equity=50)
    assert result.action is None
    assert state.phase == StrategyPhase.FLAT.value
    assert state.last_signal == "BUY"

    sell_bars = bars_from_closes(
        [100.0] * 27 + [94.0],
        opens=[99.8] * 27 + [110.0],
        start_index=28,
    )
    state.last_processed_bar_close_time = sell_bars[-2].close_time.isoformat(timespec="milliseconds")
    state.sell_condition_active = False
    result = strategy.evaluate(sell_bars, state, strategy_equity=50)
    assert result.action is None
    assert state.last_signal == "SELL"

    buy_bars = bars_from_closes([100.0] * 27 + [112.0], start_index=56)
    state.last_processed_bar_close_time = buy_bars[-2].close_time.isoformat(timespec="milliseconds")
    state.buy_condition_active = False
    result = strategy.evaluate(buy_bars, state, strategy_equity=50)
    assert result.action == LiveAction.OPEN.value


def test_rebound_on_fifth_bar_after_touch_adds():
    closes = [100.0] * 27 + [102.0]
    opens = [99.8] * 27 + [101.2]
    lows = [99.0] * 27 + [101.1]
    bars = bars_from_closes(closes, opens=opens, lows=lows)
    state = waiting_state(bars, pullback_seen=True, bars_after_touch=5)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action == LiveAction.ADD_50.value


def test_sixth_bar_rebound_does_not_add_but_next_touch_can_restart_window():
    closes = [100.0] * 27 + [101.2]
    opens = [99.8] * 27 + [102.0]
    lows = [99.0] * 27 + [101.1]
    bars = bars_from_closes(closes, opens=opens, lows=lows)
    state = waiting_state(bars, pullback_seen=True, bars_after_touch=5)
    first = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert first.action is None
    assert state.wait_add_position is True
    assert state.pullback_seen is False
    assert state.bars_after_touch == 0

    next_bars = bars_from_closes(
        [100.0] * 27 + [101.0],
        opens=[99.8] * 27 + [100.2],
        lows=[99.0] * 27 + [99.8],
        start_index=28,
    )
    state.last_processed_bar_close_time = next_bars[-2].close_time.isoformat(timespec="milliseconds")
    second = Zec4hStrategy().evaluate(next_bars, state, strategy_equity=50)
    assert second.action == LiveAction.ADD_50.value


def test_stop_uses_close_not_wick():
    closes = [100.0] * 27 + [91.0]
    lows = [99.0] * 27 + [80.0]
    bars = bars_from_closes(closes, lows=lows)
    state = full_long_state(bars, entry_low=90.0)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action is None


def test_closed_bar_below_entry_low_stops():
    bars = bars_from_closes([100.0] * 27 + [89.0])
    state = full_long_state(bars, entry_low=90.0)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action == LiveAction.STOP_CLOSE.value


def test_filled_stop_clears_attack_state_at_position_boundary():
    state = StrategyState(
        phase=StrategyPhase.LONG_FULL.value,
        actual_position_qty=1.0,
        full_position_qty=1.0,
        entry_low=90.0,
        attack_open=100.0,
        attack_close=106.0,
        attack_gain_rate=0.06,
        wait_attack_reduce=True,
    )
    Zec4hStrategy.apply_filled_action(
        state,
        decision(LiveAction.STOP_CLOSE.value),
        filled_qty=1.0,
    )
    assert state.phase == StrategyPhase.FLAT.value
    assert state.attack_open is None
    assert state.attack_close is None
    assert state.attack_gain_rate is None
    assert state.wait_attack_reduce is False
    assert "CLEAR_ATTACK_STATE_ACROSS_POSITION_BOUNDARY" in APPROVED_LIVE_SAFETY_DEVIATIONS


def test_stop_overrides_reduce_on_same_bar():
    bars = bars_from_closes([100.0] * 26 + [101.0, 89.0])
    state = full_long_state(
        bars, entry_low=90.0, attack_open=100.0, attack_close=104.0,
        attack_gain_rate=0.04, wait_attack_reduce=True,
    )
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action == LiveAction.STOP_CLOSE.value


def test_add_fill_updates_entry_low():
    state = StrategyState(
        phase=StrategyPhase.WAITING_READD.value, actual_position_qty=0.5,
        full_position_qty=1.0, reduced_qty=0.5, entry_low=80.0,
        attack_open=90.0, attack_close=96.0, attack_gain_rate=0.06,
        wait_attack_reduce=True,
    )
    Zec4hStrategy.apply_filled_action(state, decision(LiveAction.ADD_50.value, entry_low=95.0), filled_qty=0.5)
    assert state.entry_low == 95.0
    assert state.phase == StrategyPhase.LONG_FULL.value
    assert state.attack_open == 90.0
    assert state.wait_attack_reduce is True


def test_provider_forming_bar_is_rejected():
    bars = rising_signal_bars()
    last = bars[-1]
    bars[-1] = MarketBar(**{**last.__dict__, "provider_closed": False})
    with pytest.raises(ValueError, match="closed"):
        Zec4hStrategy().evaluate(bars, state_before_latest(), strategy_equity=50)


def warmup_state_and_bars() -> tuple[StrategyState, list[MarketBar]]:
    bars = bars_from_closes([100.0] * WARMUP_BARS)
    state = StrategyState()
    Zec4hStrategy().initialize_baseline(bars, state)
    return state, bars


def test_two_hundred_bar_warmup_initializes_without_order():
    state, bars = warmup_state_and_bars()
    assert state.warmup_complete is True
    assert state.warmup_bar_count == WARMUP_BARS
    assert state.last_processed_bar_close_time == bars[-1].close_time.isoformat(timespec="milliseconds")
    assert state.pending_action == ""
    assert state.actual_position_qty == 0.0
    assert state.attack_open == pytest.approx(bars[-1].open)
    assert state.attack_close == pytest.approx(bars[-1].close)
    assert state.wait_attack_reduce is True


def test_bootstrap_rebuilds_last_buy_and_blocks_same_direction_new_edge():
    history = bars_from_closes([100.0] * (WARMUP_BARS - 1) + [106.0])
    state = StrategyState()
    Zec4hStrategy().initialize_baseline(history, state)
    assert state.last_signal == "BUY"
    assert state.last_signal_open == pytest.approx(history[-1].open)
    assert state.buy_condition_active is True
    assert state.pending_action == ""
    assert state.actual_position_qty == 0.0

    # The next real bar makes BUY false without producing a valid SELL.
    false_bar_history = bars_from_closes(
        [100.0] * (WARMUP_BARS - 1) + [106.0, 101.0]
    )
    first = Zec4hStrategy().evaluate(false_bar_history, state, strategy_equity=50)
    assert first.action is None
    assert state.last_signal == "BUY"
    assert state.buy_condition_active is False
    assert state.sell_condition_active is False

    # A subsequent false->true BUY edge is rejected by rebuilt last_signal.
    next_bars = bars_from_closes(
        [100.0] * (WARMUP_BARS - 1) + [106.0, 101.0, 112.0]
    )
    result = Zec4hStrategy().evaluate(next_bars, state, strategy_equity=50)
    assert result.action is None
    assert state.last_signal == "BUY"
    assert state.phase == StrategyPhase.FLAT.value


def test_multibar_replay_updates_add_signal_and_attack_state_in_order():
    state, _ = warmup_state_and_bars()
    state.phase = StrategyPhase.WAITING_READD.value
    state.actual_position_qty = 0.5
    state.full_position_qty = 1.0
    state.reduced_qty = 0.5
    state.entry_low = 80.0
    state.wait_add_position = True
    state.last_signal = "BUY"
    closes = [100.0] * WARMUP_BARS + [100.0, 102.0, 110.0]
    opens = [99.8] * WARMUP_BARS + [100.2, 100.5, 103.0]
    lows = [99.0] * WARMUP_BARS + [99.9, 100.4, 102.5]
    bars = bars_from_closes(closes, opens=opens, lows=lows)
    replay = replay_missed_closed_bars(
        bars,
        state,
        strategy_equity=50,
        actual_position_qty=0.5,
    )
    assert replay.processed_bars == 3
    assert replay.recovery_status == "STALE_ADD_BLOCKED"
    assert any(row["status"] == "STALE_ADD_BLOCKED" for row in replay.evidence)
    assert state.actual_position_qty == pytest.approx(0.5)
    assert state.phase == StrategyPhase.LONG_REDUCED.value
    assert state.attack_open == pytest.approx(103.0)
    assert state.attack_close == pytest.approx(110.0)
    assert state.last_processed_bar_close_time == bars[-1].close_time.isoformat(timespec="milliseconds")


def test_historical_missed_open_is_evidence_only_and_stays_flat():
    state, _ = warmup_state_and_bars()
    bars = bars_from_closes([100.0] * WARMUP_BARS + [106.0, 105.0, 104.0])
    replay = replay_missed_closed_bars(
        bars,
        state,
        strategy_equity=50,
        actual_position_qty=0.0,
    )
    assert replay.recovery_status == "MISSED_STALE_ENTRY"
    assert replay.risk_reduction_decision is None
    assert any(row["status"] == "MISSED_STALE_ENTRY" for row in replay.evidence)
    assert state.phase == StrategyPhase.FLAT.value
    assert state.actual_position_qty == 0.0
    assert state.pending_action == ""


def test_multibar_replay_fails_closed_when_a_closed_bar_is_missing():
    state, _ = warmup_state_and_bars()
    bars = bars_from_closes([100.0] * WARMUP_BARS + [106.0, 105.0, 104.0])
    bars.pop(WARMUP_BARS)
    with pytest.raises(ValueError, match="gap"):
        replay_missed_closed_bars(
            bars,
            state,
            strategy_equity=50,
            actual_position_qty=0.0,
        )


def test_historical_missed_stop_with_live_long_requires_safety_exit(tmp_path: Path):
    state, _ = warmup_state_and_bars()
    state.phase = StrategyPhase.LONG_FULL.value
    state.actual_position_qty = 1.0
    state.full_position_qty = 1.0
    state.entry_low = 95.0
    bars = bars_from_closes([100.0] * WARMUP_BARS + [90.0, 89.0])
    replay = replay_missed_closed_bars(
        bars,
        state,
        strategy_equity=50,
        actual_position_qty=1.0,
    )
    assert replay.recovery_status == "SAFETY_EXIT_REQUIRED"
    assert replay.risk_reduction_decision is not None
    assert replay.risk_reduction_decision.action == LiveAction.STOP_CLOSE.value
    assert state.phase == StrategyPhase.SAFETY_EXIT_REQUIRED.value
    assert state.actual_position_qty == pytest.approx(1.0)
    assert state.recovery_decision["action"] == LiveAction.STOP_CLOSE.value
    save_strategy_state(tmp_path / "state.json", state)
    recovered = load_strategy_state(tmp_path / "state.json")
    assert recovered.recovery_status == "SAFETY_EXIT_REQUIRED"
    assert recovered.recovery_decision["signal_key"] == replay.risk_reduction_decision.signal_key
    adapter = FakeAdapter()
    adapter.position["positionAmt"] = "1"
    adapter.submit_response.update(executedQty="1", avgPrice="89")
    ledger = LiveExecutionLedger(tmp_path / "recovery.jsonl")
    engine = LiveExecutionEngine(adapter, ledger)
    persisted_before_submit = StrategyState.from_dict(recovered.to_dict())
    result = engine.execute(
        replay.risk_reduction_decision,
        recovered,
        strategy_equity=50,
        mark_price=89,
        symbol_rules=RULES,
    )
    assert result["status"] == "FILLED"
    assert recovered.phase == StrategyPhase.FLAT.value
    assert recovered.recovery_status == ""
    assert recovered.recovery_decision == {}
    # Simulate a crash after the FILLED ledger append but before state save.
    assert _recover_persisted_recovery_outcome(persisted_before_submit, ledger) is True
    assert persisted_before_submit.phase == StrategyPhase.FLAT.value
    assert persisted_before_submit.actual_position_qty == 0.0
    assert persisted_before_submit.recovery_decision == {}


def test_historical_missed_add_never_increases_half_position():
    state, _ = warmup_state_and_bars()
    state.phase = StrategyPhase.WAITING_READD.value
    state.actual_position_qty = 0.5
    state.full_position_qty = 1.0
    state.reduced_qty = 0.5
    state.entry_low = 80.0
    state.wait_add_position = True
    state.last_signal = "BUY"
    closes = [100.0] * WARMUP_BARS + [100.0, 102.0]
    opens = [99.8] * WARMUP_BARS + [100.2, 100.5]
    lows = [99.0] * WARMUP_BARS + [99.9, 100.4]
    bars = bars_from_closes(closes, opens=opens, lows=lows)
    replay = replay_missed_closed_bars(
        bars,
        state,
        strategy_equity=50,
        actual_position_qty=0.5,
    )
    assert replay.recovery_status == "STALE_ADD_BLOCKED"
    assert replay.risk_reduction_decision is None
    assert state.actual_position_qty == pytest.approx(0.5)
    assert state.phase == StrategyPhase.LONG_REDUCED.value


def test_historical_missed_reduce_can_only_return_controlled_risk_reduction():
    state, _ = warmup_state_and_bars()
    state.phase = StrategyPhase.LONG_FULL.value
    state.actual_position_qty = 1.0
    state.full_position_qty = 1.0
    state.entry_low = 80.0
    state.attack_open = 100.0
    state.attack_close = 104.0
    state.attack_gain_rate = 0.04
    state.wait_attack_reduce = True
    closes = [100.0] * (WARMUP_BARS - 1) + [101.0, 99.0, 98.5]
    bars = bars_from_closes(closes)
    replay = replay_missed_closed_bars(
        bars,
        state,
        strategy_equity=50,
        actual_position_qty=1.0,
    )
    assert replay.recovery_status == "CONTROLLED_REDUCE_REQUIRED"
    assert replay.risk_reduction_decision is not None
    assert replay.risk_reduction_decision.action == LiveAction.REDUCE_50.value
    assert replay.desired_position_qty == pytest.approx(0.5)
    assert state.actual_position_qty == pytest.approx(1.0)


@pytest.mark.parametrize("action", [
    LiveAction.OPEN.value,
    LiveAction.REDUCE_50.value,
    LiveAction.ADD_50.value,
    LiveAction.STOP_CLOSE.value,
])
def test_duplicate_actions_are_blocked(tmp_path: Path, action: str):
    adapter = FakeAdapter()
    if action in {LiveAction.REDUCE_50.value, LiveAction.STOP_CLOSE.value}:
        adapter.submit_response["executedQty"] = "0.5" if action == LiveAction.REDUCE_50.value else "1"
        adapter.position["positionAmt"] = "1"
        state = StrategyState(phase=StrategyPhase.LONG_FULL.value, actual_position_qty=1, full_position_qty=1)
    elif action == LiveAction.ADD_50.value:
        adapter.submit_response["executedQty"] = "0.5"
        adapter.position["positionAmt"] = "0.5"
        state = StrategyState(
            phase=StrategyPhase.WAITING_READD.value, actual_position_qty=0.5,
            full_position_qty=1, reduced_qty=0.5, entry_low=80.0,
        )
    else:
        state = StrategyState()
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    item = decision(action)
    first = engine.execute(item, state, strategy_equity=50, mark_price=100, symbol_rules=RULES)
    second = engine.execute(item, state, strategy_equity=50, mark_price=100, symbol_rules=RULES)
    assert first["status"] == "FILLED"
    assert second["duplicate_blocked"] is True
    assert adapter.submit_count == 1


def test_timeout_with_exchange_order_does_not_resend(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.submit_error = TimeoutError()
    adapter.query_response = {
        "status": "FILLED", "executedQty": "0.375", "avgPrice": "100", "orderId": "2001",
    }
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = engine.execute(decision(LiveAction.OPEN.value), StrategyState(), strategy_equity=50, mark_price=100, symbol_rules=RULES)
    assert result["status"] == "FILLED"
    assert adapter.submit_count == 1


def test_timeout_without_exchange_order_requires_reconciliation(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.submit_error = TimeoutError()
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = engine.execute(decision(LiveAction.OPEN.value), StrategyState(), strategy_equity=50, mark_price=100, symbol_rules=RULES)
    assert result["status"] == UNKNOWN_STATUS
    assert adapter.submit_count == 1


def test_unknown_order_retries_only_after_exchange_confirms_absent(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.submit_error = TimeoutError()
    ledger = LiveExecutionLedger(tmp_path / "live.jsonl")
    engine = LiveExecutionEngine(adapter, ledger)
    item = decision(LiveAction.OPEN.value)
    first = engine.execute(item, StrategyState(), strategy_equity=50, mark_price=100, symbol_rules=RULES)
    assert first["status"] == UNKNOWN_STATUS
    adapter.submit_error = None
    second_state = StrategyState()
    second = engine.execute(item, second_state, strategy_equity=50, mark_price=100, symbol_rules=RULES)
    assert second["status"] == "FILLED"
    assert adapter.submit_count == 2
    assert adapter.submitted[0]["client_order_id"] == adapter.submitted[1]["client_order_id"]


def test_unchanged_new_reconciliation_does_not_append_noise(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.submit_response.update(status="NEW", executedQty="0", avgPrice="0")
    ledger = LiveExecutionLedger(tmp_path / "live.jsonl")
    engine = LiveExecutionEngine(adapter, ledger)
    item = decision(LiveAction.OPEN.value)
    engine.execute(item, StrategyState(), strategy_equity=50, mark_price=100, symbol_rules=RULES)
    before = len(ledger.read())
    adapter.query_response = dict(adapter.submit_response)
    result = engine.reconcile_order(item, StrategyState(), strategy_equity=50)
    assert result["unchanged"] is True
    assert len(ledger.read()) == before


def test_missing_pending_order_is_marked_unknown_before_any_retry(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.submit_response.update(status="NEW", executedQty="0", avgPrice="0")
    ledger = LiveExecutionLedger(tmp_path / "live.jsonl")
    engine = LiveExecutionEngine(adapter, ledger)
    item = decision(LiveAction.OPEN.value)
    engine.execute(item, StrategyState(), strategy_equity=50, mark_price=100, symbol_rules=RULES)
    adapter.query_response = None
    result = engine.reconcile_order(item, StrategyState(), strategy_equity=50)
    assert result["status"] == UNKNOWN_STATUS
    assert ledger.latest_by_signal_key(item.signal_key)["status"] == UNKNOWN_STATUS
    assert adapter.submit_count == 1


def test_partial_fill_does_not_advance_strategy_state(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.submit_response.update(status="PARTIALLY_FILLED", executedQty="0.2", avgPrice="100")
    state = StrategyState()
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = engine.execute(decision(LiveAction.OPEN.value), state, strategy_equity=50, mark_price=100, symbol_rules=RULES)
    assert result["status"] == "PARTIALLY_FILLED"
    assert state.phase == StrategyPhase.FLAT.value


def test_rejected_order_clears_pending_without_position_change(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.submit_response.update(status="REJECTED", executedQty="0", avgPrice="0")
    state = StrategyState(pending_action=LiveAction.OPEN.value)
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = engine.execute(decision(LiveAction.OPEN.value), state, strategy_equity=50, mark_price=100, symbol_rules=RULES)
    assert result["status"] == "REJECTED"
    assert state.pending_action == ""
    assert state.phase == StrategyPhase.HARD_STOP.value
    assert state.hard_stop_reason == "ORDER_REJECTED"


def test_expired_partial_fill_tracks_exchange_exposure_and_hard_stops(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.submit_response.update(status="EXPIRED", executedQty="0.2", avgPrice="100")
    state = StrategyState(pending_action=LiveAction.OPEN.value)
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = engine.execute(decision(LiveAction.OPEN.value), state, strategy_equity=50, mark_price=100, symbol_rules=RULES)
    assert result["status"] == "EXPIRED"
    assert state.actual_position_qty == pytest.approx(0.2)
    assert state.phase == StrategyPhase.HARD_STOP.value


@pytest.mark.parametrize("terminal_status", ["CANCELED", "EXPIRED", "EXPIRED_IN_MATCH"])
def test_partial_terminal_immediately_submits_hard_stop_close(tmp_path: Path, terminal_status: str):
    adapter = FakeAdapter()
    adapter.submit_responses = [
        {"status": terminal_status, "executedQty": "0.2", "avgPrice": "100", "orderId": "p1"},
        {"status": "FILLED", "executedQty": "0.2", "avgPrice": "99", "orderId": "p2"},
    ]
    state = StrategyState()
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = _execute_with_immediate_safety_exit(
        engine,
        decision(LiveAction.OPEN.value),
        state,
        strategy_equity=50,
        mark_price=100,
        symbol_rules=RULES,
    )
    assert result["immediate_safety_exit"] is True
    assert result["primary"]["status"] == terminal_status
    assert result["safety_exit"]["status"] == "FILLED"
    assert adapter.submit_count == 2
    assert float(adapter.position["positionAmt"]) == pytest.approx(0.0)
    assert state.phase == StrategyPhase.HARD_STOP.value
    assert state.actual_position_qty == 0.0


def test_partial_terminal_crash_recovers_then_closes_without_waiting_for_bar(tmp_path: Path):
    ledger = LiveExecutionLedger(tmp_path / "live.jsonl")
    item = decision(LiveAction.OPEN.value)
    ledger.append({
        "strategy_id": "zec_4h_live_v1",
        "signal_key": item.signal_key,
        "bar_close_time": item.bar_close_time,
        "action": item.action,
        "status": "EXPIRED",
        "requested_qty": 0.48,
        "filled_qty": 0.2,
        "average_fill_price": 100.0,
        "client_order_id": item.client_order_id,
        "exchange_order_id": "partial-crash",
        "signal_price": item.signal_price,
        "entry_low": item.entry_low,
        "recorded_at": "2026-08-24T16:00:01.000+00:00",
    })
    adapter = FakeAdapter()
    adapter.position["positionAmt"] = "0.2"
    state = StrategyState(
        pending_action=item.action,
        pending_decision=dict(item.__dict__),
    )
    recovered = recover_unapplied_filled_transitions(state, ledger, adapter)
    assert recovered["ok"] is True
    assert recovered["recovered"] == 1
    assert state.recovery_status == "PARTIAL_TERMINAL_SAFETY_EXIT_REQUIRED"
    assert state.actual_position_qty == pytest.approx(0.2)

    adapter.submit_response.update(status="FILLED", executedQty="0.2", avgPrice="99")
    engine = LiveExecutionEngine(adapter, ledger)
    safety = _execute_with_immediate_safety_exit(
        engine,
        _decision_from_record(state.recovery_decision),
        state,
        strategy_equity=50,
        mark_price=99,
        symbol_rules=RULES,
    )
    assert safety["status"] == "FILLED"
    assert adapter.submit_count == 1
    assert state.actual_position_qty == 0.0


def test_restart_reconciliation_passes_matching_position(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.position["positionAmt"] = "1"
    state = StrategyState(
        phase=StrategyPhase.LONG_FULL.value,
        actual_position_qty=1,
        full_position_qty=1,
        entry_low=80.0,
    )
    result = reconcile_startup(state, LiveExecutionLedger(tmp_path / "live.jsonl"), adapter)
    assert result["ok"] is True
    assert state.stop_guard_active is True
    assert state.stop_guard_price == 80.0


def test_restart_reconciliation_blocks_unprotected_position(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.position["positionAmt"] = "1"
    state = StrategyState(
        phase=StrategyPhase.LONG_FULL.value,
        actual_position_qty=1,
        full_position_qty=1,
        entry_low=None,
    )
    result = reconcile_startup(state, LiveExecutionLedger(tmp_path / "live.jsonl"), adapter)
    assert result == {"ok": False, "reason": "STOP_GUARD_PRICE_UNAVAILABLE"}


def test_open_fill_arms_closed_bar_stop_guard(tmp_path: Path):
    adapter = FakeAdapter()
    state = StrategyState()
    result = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl")).execute(
        decision(LiveAction.OPEN.value, entry_low=90.0), state,
        strategy_equity=50, mark_price=100, symbol_rules=RULES,
    )
    assert result["status"] == "FILLED"
    assert state.stop_guard_active is True
    assert state.stop_guard_price == 90.0


def test_open_fill_without_stop_guard_requires_immediate_safety_exit(tmp_path: Path):
    adapter = FakeAdapter()
    state = StrategyState()
    result = _execute_with_immediate_safety_exit(
        LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl")),
        decision(LiveAction.OPEN.value, entry_low=None),
        state,
        strategy_equity=50,
        mark_price=100,
        symbol_rules=RULES,
    )
    assert result["immediate_safety_exit"] is True
    assert result["safety_exit"]["status"] == "FILLED"
    assert float(adapter.position["positionAmt"]) == 0.0


@pytest.mark.parametrize(
    "action,before_qty,filled_qty,after_qty,before_phase",
    [
        (LiveAction.OPEN.value, 0.0, 1.0, 1.0, StrategyPhase.FLAT.value),
        (LiveAction.REDUCE_50.value, 1.0, 0.5, 0.5, StrategyPhase.LONG_FULL.value),
        (LiveAction.ADD_50.value, 0.5, 0.5, 1.0, StrategyPhase.WAITING_READD.value),
        (LiveAction.STOP_CLOSE.value, 1.0, 1.0, 0.0, StrategyPhase.LONG_FULL.value),
        (LiveAction.HARD_STOP_CLOSE.value, 1.0, 1.0, 0.0, StrategyPhase.LONG_FULL.value),
    ],
)
def test_generic_filled_crash_recovery_applies_exactly_once(
    tmp_path: Path,
    action: str,
    before_qty: float,
    filled_qty: float,
    after_qty: float,
    before_phase: str,
):
    state = StrategyState(
        phase=before_phase,
        actual_position_qty=before_qty,
        full_position_qty=1.0 if before_qty else 0.0,
        reduced_qty=0.5 if action == LiveAction.ADD_50.value else 0.0,
        entry_low=80.0 if before_qty else None,
    )
    item = decision(action, entry_low=95.0)
    state.pending_action = action
    state.pending_decision = dict(item.__dict__)
    ledger = LiveExecutionLedger(tmp_path / "live.jsonl")
    ledger.append({
        "strategy_id": "zec_4h_live_v1",
        "signal_key": item.signal_key,
        "bar_close_time": item.bar_close_time,
        "action": action,
        "status": "FILLED",
        "requested_qty": filled_qty,
        "filled_qty": filled_qty,
        "average_fill_price": 100.0,
        "client_order_id": item.client_order_id,
        "exchange_order_id": f"filled-{action}",
        "signal_price": item.signal_price,
        "entry_low": item.entry_low,
        "recorded_at": "2026-08-24T16:00:01.000+00:00",
    })
    adapter = FakeAdapter()
    adapter.position["positionAmt"] = str(after_qty)
    first = recover_unapplied_filled_transitions(state, ledger, adapter)
    snapshot = state.to_dict()
    second = recover_unapplied_filled_transitions(state, ledger, adapter)
    assert first["ok"] is True
    assert first["recovered"] == 1
    assert second == {"ok": True, "recovered": 0}
    assert state.to_dict() == snapshot
    assert state.actual_position_qty == pytest.approx(after_qty)
    assert state.applied_fill_signal_keys == [item.signal_key]
    assert state.pending_decision == {}
    assert adapter.submit_count == 0
    assert reconcile_startup(state, ledger, adapter)["ok"] is True


def test_generic_fill_recovery_does_not_replay_pre_upgrade_history(tmp_path: Path):
    state = StrategyState(
        phase=StrategyPhase.LONG_FULL.value,
        actual_position_qty=1.0,
        full_position_qty=1.0,
        entry_low=90.0,
    )
    historical = decision(LiveAction.OPEN.value)
    ledger = LiveExecutionLedger(tmp_path / "live.jsonl")
    ledger.append({
        "strategy_id": "zec_4h_live_v1",
        "signal_key": historical.signal_key,
        "bar_close_time": historical.bar_close_time,
        "action": historical.action,
        "status": "FILLED",
        "requested_qty": 1.0,
        "filled_qty": 1.0,
        "average_fill_price": 100.0,
        "client_order_id": historical.client_order_id,
        "exchange_order_id": "historical-fill",
        "signal_price": historical.signal_price,
        "entry_low": historical.entry_low,
        "recorded_at": "2026-08-20T16:00:01.000+00:00",
    })
    adapter = FakeAdapter()
    adapter.position["positionAmt"] = "1.0"
    before = state.to_dict()
    recovered = recover_unapplied_filled_transitions(state, ledger, adapter)
    assert recovered == {"ok": True, "recovered": 0}
    assert state.to_dict() == before


def test_exchange_local_disagreement_fails_closed(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.position["positionAmt"] = "1"
    result = reconcile_startup(StrategyState(), LiveExecutionLedger(tmp_path / "live.jsonl"), adapter)
    assert result["ok"] is False
    assert "MISMATCH" in result["reason"] or "POSITION" in result["reason"]


def test_unrecognized_exchange_open_order_fails_closed(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.open_orders = [{"clientOrderId": "external-order"}]
    result = reconcile_startup(StrategyState(), LiveExecutionLedger(tmp_path / "live.jsonl"), adapter)
    assert result == {"ok": False, "reason": "UNRECOGNIZED_EXCHANGE_OPEN_ORDER"}


def test_initial_order_uses_exactly_one_percent_margin_and_never_scales_above_cap(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.account["totalMarginBalance"] = "500"
    adapter.account["totalWalletBalance"] = "500"
    adapter.available_balance = 500
    state = StrategyState()
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    engine.execute(decision(LiveAction.OPEN.value), state, strategy_equity=500, mark_price=100, symbol_rules=RULES)
    assert adapter.submit_count == 1
    latest = engine.ledger.read()[-1]
    assert LIVE_CAPITAL_CAP_USDT == 50.0
    assert TARGET_INITIAL_MARGIN_USDT == 0.5
    assert latest["requested_qty"] * 100 == pytest.approx(0.5 * 75)


@pytest.mark.parametrize(
    "rules,expected_qty",
    [
        ({**RULES, "step_size": 0.01, "min_qty": 0.01}, 0.37),
        ({**RULES, "step_size": 0.5, "min_qty": 0.5}, 0.0),
    ],
)
def test_initial_quantity_obeys_step_size_and_min_qty_without_raising_margin(
    tmp_path: Path, rules: dict, expected_qty: float,
):
    adapter = FakeAdapter()
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = engine.execute(
        decision(LiveAction.OPEN.value), StrategyState(), strategy_equity=50,
        mark_price=100, symbol_rules=rules,
    )
    if expected_qty == 0:
        assert result["submitted"] is False
        assert adapter.submit_count == 0
    else:
        assert engine.ledger.read()[-1]["requested_qty"] == pytest.approx(expected_qty)
        assert engine.ledger.read()[-1]["requested_qty"] * 100 <= 0.5 * 75


def test_reduce_quantity_never_crosses_original_half_target():
    state = StrategyState(
        phase=StrategyPhase.LONG_FULL.value,
        actual_position_qty=0.6,
        full_position_qty=1.0,
    )
    qty = LiveExecutionEngine._requested_qty(
        LiveAction.REDUCE_50.value,
        state,
        strategy_equity=50,
        exchange_available_balance=50,
        mark_price=100,
        symbol_rules=RULES,
    )
    assert qty <= 0.1 + 1e-12
    assert state.actual_position_qty - qty >= 0.5 - 1e-12


@pytest.mark.parametrize(
    "actual_qty,step_size,expected_qty",
    [
        (0.6004, 0.001, 0.100),
        (0.6004, 0.01, 0.10),
        (0.5004, 0.001, 0.0),
        (0.61, 0.07, 0.07),
    ],
)
def test_reduce_step_rounding_preserves_half_floor(actual_qty, step_size, expected_qty):
    rules = {**RULES, "step_size": step_size, "min_qty": step_size}
    state = StrategyState(
        phase=StrategyPhase.LONG_FULL.value,
        actual_position_qty=actual_qty,
        full_position_qty=1.0,
    )
    qty = LiveExecutionEngine._requested_qty(
        LiveAction.REDUCE_50.value,
        state,
        strategy_equity=50,
        exchange_available_balance=50,
        mark_price=100,
        symbol_rules=rules,
    )
    assert qty == pytest.approx(expected_qty)
    assert actual_qty - qty >= 0.5 - 1e-12


def test_strategy_equity_excludes_unrelated_account_deposits():
    records = [
        {"signal_key": "open", "status": "FILLED", "realized_pnl": 0, "fee": 0.02},
        {"signal_key": "funding", "status": "ACCOUNT_INCOME", "funding": -0.03},
        {"signal_key": "reduce", "status": "FILLED", "realized_pnl": 1.0, "fee": 0.01},
    ]
    position = {"positionAmt": "0.5", "unRealizedProfit": "0.50"}
    # The exchange account could contain 500 USDT; it is intentionally not an
    # input to this calculation and therefore cannot enlarge strategy budget.
    assert strategy_equity_from_evidence(records, position) == pytest.approx(51.44)
    assert verify_dedicated_account_boundary(exchange_equity=500, strategy_equity=51.44)["ok"] is False


def test_hard_floor_flattens_then_locks():
    bars = rising_signal_bars()
    state = full_long_state(bars)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=30)
    assert result.action == LiveAction.HARD_STOP_CLOSE.value
    Zec4hStrategy.apply_filled_action(state, result, filled_qty=1)
    assert state.phase == StrategyPhase.HARD_STOP.value


def test_hard_floor_remains_active_between_bar_transitions():
    bars = rising_signal_bars()
    state = full_long_state(bars)
    state.last_processed_bar_close_time = bars[-1].close_time.isoformat(timespec="milliseconds")
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=29.99)
    assert result.action == LiveAction.HARD_STOP_CLOSE.value


def test_runner_hard_floor_closes_on_poll_without_new_closed_bar(tmp_path: Path, monkeypatch):
    bars = bars_from_closes([100.0] * WARMUP_BARS)
    state = StrategyState()
    Zec4hStrategy().initialize_baseline(bars, state)
    state.phase = StrategyPhase.LONG_FULL.value
    state.actual_position_qty = 1.0
    state.full_position_qty = 1.0
    state.entry_low = 80.0
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "live.jsonl"
    scorecard_path = tmp_path / "scorecard.json"
    save_strategy_state(state_path, state)

    adapter = FakeAdapter()
    adapter.position.update(positionAmt="1", unRealizedProfit="-20")
    adapter.account.update(
        totalMarginBalance="30",
        totalWalletBalance="30",
        totalUnrealizedProfit="-20",
    )
    adapter.submit_response.update(status="FILLED", executedQty="1", avgPrice="100")

    class PublicSource:
        def get_bars(self, symbol, timeframe, limit):
            assert limit >= WARMUP_BARS
            return list(bars)

    monkeypatch.setattr(live_runner, "_assert_activation", lambda: None)
    monkeypatch.setattr(live_runner, "_adapter", lambda live_enabled: adapter)
    monkeypatch.setattr(live_runner, "run_live_preflight", lambda *args, **kwargs: {"preflight_pass": True})
    monkeypatch.setattr(live_runner, "BinancePublicKlineAdapter", lambda config: PublicSource())
    before_boundary = state.last_processed_bar_close_time
    result = live_runner.run_cycle(
        state_path=state_path,
        ledger_path=ledger_path,
        scorecard_path=scorecard_path,
    )
    persisted = load_strategy_state(state_path)
    assert result["result"]["status"] == "FILLED"
    assert adapter.submit_count == 1
    assert adapter.submitted[0]["side"] == "SELL"
    assert adapter.submitted[0]["reduce_only"] is True
    assert persisted.phase == StrategyPhase.HARD_STOP.value
    assert persisted.actual_position_qty == 0.0
    assert persisted.last_processed_bar_close_time == before_boundary


def test_runner_partial_terminal_executes_safety_exit_in_same_cycle(tmp_path: Path, monkeypatch):
    baseline = bars_from_closes([100.0] * WARMUP_BARS)
    all_bars = bars_from_closes([100.0] * WARMUP_BARS + [106.0])
    state = StrategyState()
    Zec4hStrategy().initialize_baseline(baseline, state)
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "live.jsonl"
    scorecard_path = tmp_path / "scorecard.json"
    save_strategy_state(state_path, state)

    adapter = FakeAdapter()
    adapter.submit_responses = [
        {"status": "EXPIRED", "executedQty": "0.2", "avgPrice": "106", "orderId": "runner-p1"},
        {"status": "FILLED", "executedQty": "0.2", "avgPrice": "105", "orderId": "runner-p2"},
    ]

    class PublicSource:
        def get_bars(self, symbol, timeframe, limit):
            return list(all_bars)

    monkeypatch.setattr(live_runner, "_assert_activation", lambda: None)
    monkeypatch.setattr(live_runner, "_adapter", lambda live_enabled: adapter)
    monkeypatch.setattr(live_runner, "run_live_preflight", lambda *args, **kwargs: {"preflight_pass": True})
    monkeypatch.setattr(live_runner, "BinancePublicKlineAdapter", lambda config: PublicSource())
    result = live_runner.run_cycle(
        state_path=state_path,
        ledger_path=ledger_path,
        scorecard_path=scorecard_path,
    )
    persisted = load_strategy_state(state_path)
    assert result["result"]["immediate_safety_exit"] is True
    assert result["result"]["primary"]["status"] == "EXPIRED"
    assert result["result"]["safety_exit"]["status"] == "FILLED"
    assert adapter.submit_count == 2
    assert float(adapter.position["positionAmt"]) == 0.0
    assert persisted.phase == StrategyPhase.HARD_STOP.value
    assert persisted.actual_position_qty == 0.0


def test_target_equity_pauses_new_entries():
    state = state_before_latest()
    result = Zec4hStrategy().evaluate(rising_signal_bars(), state, strategy_equity=150)
    assert result.action is None
    assert state.phase == StrategyPhase.TARGET_REACHED_PAUSED.value


def test_state_round_trip_is_atomic_and_complete(tmp_path: Path):
    path = tmp_path / "state.json"
    state = StrategyState(
        phase=StrategyPhase.WAITING_READD.value,
        last_signal="BUY", last_signal_open=99, bars_since_signal=3,
        wait_add_position=True, pullback_seen=True, bars_after_touch=2,
        entry_low=88, last_processed_bar_close_time="2026-08-24T16:00:00.000+00:00",
    )
    save_strategy_state(path, state)
    assert load_strategy_state(path) == state
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_live_ledger_and_scorecard_use_actual_fields(tmp_path: Path):
    ledger = LiveExecutionLedger(tmp_path / "live.jsonl")
    ledger.append({
        "strategy_id": "zec_4h_live_v1", "signal_key": "open", "bar_close_time": "t1",
        "action": "OPEN", "status": "FILLED", "recorded_at": "1",
        "filled_qty": 0.5,
        "realized_pnl": 0, "net_realized_pnl": -0.1, "fee": 0.1, "funding": 0,
        "realized_slippage": 0.02, "strategy_equity_after": 49.9,
    })
    ledger.append({
        "strategy_id": "zec_4h_live_v1", "signal_key": "funding", "bar_close_time": "t2",
        "action": "FUNDING_PAYMENT", "status": "ACCOUNT_INCOME", "recorded_at": "2",
        "filled_qty": 0,
        "realized_pnl": 0, "net_realized_pnl": -0.1, "fee": 0, "funding": -0.1,
        "realized_slippage": 0, "strategy_equity_after": 49.8,
    })
    ledger.append({
        "strategy_id": "zec_4h_live_v1", "signal_key": "close", "bar_close_time": "t3",
        "action": "STOP_CLOSE", "status": "FILLED", "recorded_at": "3",
        "filled_qty": 0.5,
        "realized_pnl": 2, "net_realized_pnl": 1.8, "fee": 0.2, "funding": 0,
        "realized_slippage": 0.05, "strategy_equity_after": 51.8,
    })
    score = build_live_scorecard(
        ledger.read(), current_equity=51.8, current_position={}, current_open_orders=[], strategy_state=StrategyState()
    )
    assert score["closed_trades"] == 1
    assert score["actual_fees"] == pytest.approx(0.3)
    assert score["actual_funding"] == pytest.approx(-0.1)
    assert score["net_expectancy"] == pytest.approx(1.6)
    assert oct(ledger.path.stat().st_mode & 0o777) == "0o600"


def test_funding_income_sync_is_idempotent(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.income = [{"tranId": 77, "time": 1_700_000_000_000, "income": "-0.012", "asset": "USDT"}]
    ledger = LiveExecutionLedger(tmp_path / "live.jsonl")
    engine = LiveExecutionEngine(adapter, ledger)
    assert engine.sync_funding_income()["appended"] == 1
    assert engine.sync_funding_income()["appended"] == 0
    assert ledger.read()[0]["funding"] == pytest.approx(-0.012)


def test_binance_response_schema_and_write_guard():
    calls = []

    def transport(request):
        calls.append((request["method"], request["path"]))
        path = request["path"]
        if path == "/fapi/v3/account": return {"ok": True, "data": {"canTrade": True}}
        if path == "/fapi/v3/balance": return {"ok": True, "data": [{"asset": "USDT"}]}
        if path == "/fapi/v3/positionRisk": return {"ok": True, "data": [{"symbol": "ZECUSDT", "positionAmt": "0"}]}
        if path == "/fapi/v1/openOrders": return {"ok": True, "data": []}
        if path == "/fapi/v1/exchangeInfo": return {"ok": True, "data": exchange_info_fixture()}
        if path == "/fapi/v1/time": return {"ok": True, "data": {"serverTime": 1}}
        if path == "/fapi/v1/leverageBracket": return {"ok": True, "data": [{
            "symbol": "ZECUSDT",
            "brackets": [{"initialLeverage": 75, "notionalFloor": 0, "notionalCap": 10000}],
        }]}
        if path == "/fapi/v1/symbolConfig": return {"ok": True, "data": [{
            "symbol": "ZECUSDT", "marginType": "ISOLATED", "leverage": 75,
        }]}
        raise AssertionError(path)

    adapter = BinanceUsdMExecutionAdapter(api_key="fixture", api_secret="fixture", transport=transport)
    assert adapter.get_account()["canTrade"] is True
    assert adapter.get_balance()[0]["asset"] == "USDT"
    assert adapter.get_position()["positionAmt"] == "0"
    assert adapter.get_open_orders() == []
    assert resolve_max_allowed_leverage(adapter.get_leverage_brackets()) == 75
    assert adapter.get_symbol_config()["marginType"] == "ISOLATED"
    assert extract_symbol_rules(adapter.get_exchange_info())["min_notional"] == 5
    with pytest.raises(RuntimeError, match="DISABLED"):
        adapter.submit_market_order(
            side="BUY", quantity=0.1, client_order_id="fixture", reduce_only=False,
        )


def test_preflight_requires_every_safety_check():
    adapter = FakeAdapter()
    result = run_live_preflight(
        adapter,
        withdrawal_disabled_verified=True,
        local_time_ms=int(BASE.timestamp() * 1000),
    )
    assert result["preflight_pass"] is True
    assert result["api_authentication"] is True
    assert result["futures_account_access"] is True
    assert result["futures_trading_permission"] is True
    assert result["withdraw_permission"] == "OFF"
    adapter.position["leverage"] = "10"
    blocked = run_live_preflight(
        adapter,
        withdrawal_disabled_verified=True,
        local_time_ms=int(BASE.timestamp() * 1000),
    )
    assert blocked["preflight_pass"] is False
    assert blocked["leverage_max_allowed"] is False


def test_preflight_blocks_unknown_leverage_bracket_and_withdraw_permission():
    adapter = FakeAdapter()
    adapter.get_leverage_brackets = lambda symbol="ZECUSDT": []
    unknown = run_live_preflight(adapter, local_time_ms=int(BASE.timestamp() * 1000))
    assert unknown["preflight_pass"] is False
    assert unknown["error"] == "ValueError"

    adapter = FakeAdapter()
    adapter.get_api_restrictions = lambda: {
        "enableFutures": True, "enableWithdrawals": True, "ipRestrict": True,
    }
    withdrawal = run_live_preflight(adapter, local_time_ms=int(BASE.timestamp() * 1000))
    assert withdrawal["preflight_pass"] is False
    assert withdrawal["withdrawal_disabled_verified"] is False
    assert withdrawal["withdraw_permission"] == "ON"


def test_preflight_parses_futures_permission_and_authentication_failure():
    adapter = FakeAdapter()
    adapter.account["canTrade"] = False
    denied = run_live_preflight(adapter, local_time_ms=int(BASE.timestamp() * 1000))
    assert denied["api_authentication"] is True
    assert denied["futures_account_access"] is True
    assert denied["futures_trading_permission"] is False
    assert denied["preflight_pass"] is False

    adapter = FakeAdapter()
    def authentication_error():
        raise RuntimeError("AUTHENTICATION_FAILED")
    adapter.get_account = authentication_error
    failed = run_live_preflight(adapter, local_time_ms=int(BASE.timestamp() * 1000))
    assert failed["api_authentication"] is False
    assert failed["futures_account_access"] is False
    assert failed["futures_trading_permission"] is False
    assert failed["withdraw_permission"] == "UNKNOWN"


def test_max_leverage_resolution_respects_position_notional_bracket():
    payload = [{
        "symbol": "ZECUSDT",
        "brackets": [
            {"initialLeverage": 125, "notionalFloor": 0, "notionalCap": 50},
            {"initialLeverage": 50, "notionalFloor": 50, "notionalCap": 10000},
        ],
    }]
    assert resolve_max_allowed_leverage(payload, initial_margin_usdt=0.5) == 99


def test_minimum_notional_never_increases_the_one_percent_margin(tmp_path: Path):
    adapter = FakeAdapter()
    rules = {**RULES, "min_notional": 50.0}
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = engine.execute(
        decision(LiveAction.OPEN.value), StrategyState(), strategy_equity=500,
        mark_price=100, symbol_rules=rules,
    )
    assert result["submitted"] is False
    assert result["reason"] == "INVALID_OR_ZERO_QUANTITY"
    assert adapter.submit_count == 0


@pytest.mark.parametrize("drift", ["LEVERAGE_10X", "CROSS_MARGIN", "HEDGE_MODE"])
def test_runtime_invariant_drift_blocks_every_new_order(tmp_path: Path, drift: str):
    adapter = FakeAdapter()
    if drift == "LEVERAGE_10X":
        adapter.position["leverage"] = "10"
    elif drift == "CROSS_MARGIN":
        adapter.position["isolated"] = False
        adapter.position["marginType"] = "cross"
    else:
        adapter.dual_side_position = True
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    result = engine.execute(
        decision(LiveAction.OPEN.value),
        StrategyState(),
        strategy_equity=50,
        mark_price=100,
        symbol_rules=RULES,
    )
    assert result["ok"] is False
    assert result["submitted"] is False
    assert result["reason"] == "RUNTIME_INVARIANT_BLOCKED"
    assert adapter.submit_count == 0
