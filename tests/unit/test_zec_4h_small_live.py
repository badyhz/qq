from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.paper_trading.data_source import MarketBar
from core.zec_4h_live import (
    LiveAction,
    LiveExecutionLedger,
    StrategyDecision,
    StrategyPhase,
    StrategyState,
    Zec4hStrategy,
    build_live_scorecard,
    load_strategy_state,
    save_strategy_state,
)
from core.zec_4h_live_execution import (
    BinanceUsdMExecutionAdapter,
    LiveExecutionEngine,
    UNKNOWN_STATUS,
    extract_symbol_rules,
    reconcile_startup,
    run_live_preflight,
    strategy_equity_from_evidence,
    verify_dedicated_account_boundary,
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
            "status": "FILLED", "executedQty": "0.48", "avgPrice": "100",
            "orderId": "1001", "clientOrderId": "fake",
        }
        self.submit_error: Exception | None = None
        self.query_response = None
        self.position = {"symbol": "ZECUSDT", "positionAmt": "0", "isolated": True, "leverage": "1"}
        self.open_orders = []
        self.account = {
            "canTrade": True,
            "totalMarginBalance": "50",
            "totalWalletBalance": "50",
            "totalUnrealizedProfit": "0",
        }
        self.fills = []
        self.income = []
        self.submitted = []

    def get_account(self): return dict(self.account)
    def get_balance(self): return [{"asset": "USDT", "balance": "50"}]
    def get_position(self, symbol="ZECUSDT"): return dict(self.position)
    def get_open_orders(self, symbol="ZECUSDT"): return [dict(row) for row in self.open_orders]
    def get_exchange_info(self): return exchange_info_fixture()
    def get_server_time(self): return {"serverTime": int(BASE.timestamp() * 1000)}
    def get_position_mode(self): return {"dualSidePosition": False}
    def get_api_restrictions(self):
        return {"enableFutures": True, "enableWithdrawals": False, "ipRestrict": True}
    def set_leverage(self, leverage, symbol="ZECUSDT"): return {"leverage": leverage, "symbol": symbol}
    def set_margin_type(self, margin_type, symbol="ZECUSDT"): return {"code": 200}

    def submit_market_order(self, **kwargs):
        self.submit_count += 1
        self.submitted.append(dict(kwargs))
        if self.submit_error:
            raise self.submit_error
        row = dict(self.submit_response)
        row["clientOrderId"] = kwargs["client_order_id"]
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
    state = StrategyState(phase=StrategyPhase.LONG_FULL.value, actual_position_qty=1, full_position_qty=1)
    Zec4hStrategy.apply_filled_action(state, decision(LiveAction.REDUCE_50.value), filled_qty=0.5)
    assert state.phase == StrategyPhase.WAITING_READD.value
    assert state.wait_add_position is True
    assert state.actual_position_qty == pytest.approx(0.5)
    assert state.wait_attack_reduce is False


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


def test_add_wait_expires_after_five_bars():
    bars = readd_bars(current_close=100.0, current_open=100.2, current_low=99.9)
    state = waiting_state(bars, pullback_seen=True, bars_after_touch=4)
    result = Zec4hStrategy().evaluate(bars, state, strategy_equity=50)
    assert result.action is None
    assert state.wait_add_position is False
    assert state.phase == StrategyPhase.LONG_REDUCED.value


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
    )
    Zec4hStrategy.apply_filled_action(state, decision(LiveAction.ADD_50.value, entry_low=95.0), filled_qty=0.5)
    assert state.entry_low == 95.0
    assert state.phase == StrategyPhase.LONG_FULL.value


def test_provider_forming_bar_is_rejected():
    bars = rising_signal_bars()
    last = bars[-1]
    bars[-1] = MarketBar(**{**last.__dict__, "provider_closed": False})
    with pytest.raises(ValueError, match="closed"):
        Zec4hStrategy().evaluate(bars, state_before_latest(), strategy_equity=50)


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
        state = StrategyState(phase=StrategyPhase.LONG_FULL.value, actual_position_qty=1, full_position_qty=1)
    elif action == LiveAction.ADD_50.value:
        adapter.submit_response["executedQty"] = "0.5"
        state = StrategyState(
            phase=StrategyPhase.WAITING_READD.value, actual_position_qty=0.5,
            full_position_qty=1, reduced_qty=0.5,
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
        "status": "FILLED", "executedQty": "0.48", "avgPrice": "100", "orderId": "2001",
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


def test_restart_reconciliation_passes_matching_position(tmp_path: Path):
    adapter = FakeAdapter()
    adapter.position["positionAmt"] = "1"
    state = StrategyState(phase=StrategyPhase.LONG_FULL.value, actual_position_qty=1, full_position_qty=1)
    result = reconcile_startup(state, LiveExecutionLedger(tmp_path / "live.jsonl"), adapter)
    assert result["ok"] is True


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


def test_initial_order_reserves_buffer_and_never_exceeds_50(tmp_path: Path):
    adapter = FakeAdapter()
    state = StrategyState()
    engine = LiveExecutionEngine(adapter, LiveExecutionLedger(tmp_path / "live.jsonl"))
    engine.execute(decision(LiveAction.OPEN.value), state, strategy_equity=50, mark_price=100, symbol_rules=RULES)
    submitted = adapter.submit_response
    assert adapter.submit_count == 1
    latest = engine.ledger.read()[-1]
    assert latest["requested_qty"] * 100 <= 48.0 + 1e-9


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
        raise AssertionError(path)

    adapter = BinanceUsdMExecutionAdapter(api_key="fixture", api_secret="fixture", transport=transport)
    assert adapter.get_account()["canTrade"] is True
    assert adapter.get_balance()[0]["asset"] == "USDT"
    assert adapter.get_position()["positionAmt"] == "0"
    assert adapter.get_open_orders() == []
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
    adapter.account["totalMarginBalance"] = "70"
    blocked = run_live_preflight(
        adapter,
        withdrawal_disabled_verified=True,
        local_time_ms=int(BASE.timestamp() * 1000),
    )
    assert blocked["preflight_pass"] is False
    assert blocked["strategy_budget_ok"] is False
