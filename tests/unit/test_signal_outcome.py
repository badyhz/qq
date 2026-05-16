from __future__ import annotations

import json
from typing import Any

import pytest

from core.signal_outcome import (
    build_shadow_order_outcome_rows,
    dedupe_shadow_order_plans,
    evaluate_signal_forward_outcome,
    normalize_shadow_order_plan,
    parse_shadow_order_plan,
    summarize_outcomes_by_horizon,
    summarize_outcomes_by_symbol,
    summarize_outcomes_by_time_bucket,
    summarize_outcomes_for_primary_horizon,
    summarize_shadow_order_outcomes,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _trending_klines(symbol: str = "BTCUSDT", bars: int = 60, start_price: float = 100.0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(bars):
        close = start_price + i * 0.5
        rows.append({
            "symbol": symbol,
            "timestamp": 1700000000000 + i * 300000,
            "open": close - 0.2,
            "high": close + 0.3,
            "low": close - 0.8,
            "close": close,
            "volume": 1000.0 + i * 10,
        })
    return rows


def _flat_klines(symbol: str = "BTCUSDT", bars: int = 60, price: float = 100.0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(bars):
        rows.append({
            "symbol": symbol,
            "timestamp": 1700000000000 + i * 300000,
            "open": price,
            "high": price + 0.1,
            "low": price - 0.1,
            "close": price,
            "volume": 1000.0,
        })
    return rows


# ---------------------------------------------------------------------------
# evaluate_signal_forward_outcome
# ---------------------------------------------------------------------------

class TestEvaluateSignalForwardOutcome:
    def test_basic_long_tp_hit(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        future = _trending_klines(bars=20, start_price=100.0)
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[15])
        r = outcome["per_horizon_results"]["15"]
        assert r["hit_take_profit"] is True

    def test_basic_short_tp_hit(self):
        signal = {"symbol": "BTCUSDT", "side": "SHORT", "entry_price": 100.0, "stop_loss": 105.0, "take_profit": 95.0}
        future = [
            {"timestamp": 1, "open": 100, "high": 100.1, "low": 94.5, "close": 95, "volume": 1000},
        ]
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[1])
        r = outcome["per_horizon_results"]["1"]
        assert r["hit_take_profit"] is True

    def test_same_bar_tp_and_sl_returns_stop_loss_first(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        future = [{"timestamp": 1, "open": 100, "high": 106, "low": 94, "close": 101, "volume": 1000}]
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[1])
        r = outcome["per_horizon_results"]["1"]
        assert r["first_hit"] == "stop_loss_first"
        assert r["hit_take_profit"] is True
        assert r["hit_stop_loss"] is True

    def test_rr_target_rebuilds_take_profit(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 120.0}
        future = [
            {"timestamp": 1, "open": 100, "high": 104.9, "low": 99.2, "close": 104, "volume": 1000},
            {"timestamp": 2, "open": 104, "high": 105.2, "low": 103.8, "close": 105, "volume": 900},
        ]
        base = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[2])
        tuned = evaluate_signal_forward_outcome(
            signal=signal, future_klines=future, horizons=[2], exit_params={"rr_target": 1.0},
        )
        assert base["per_horizon_results"]["2"]["hit_take_profit"] is False
        assert tuned["per_horizon_results"]["2"]["hit_take_profit"] is True
        assert tuned["per_horizon_results"]["2"]["effective_take_profit"] == 105.0

    def test_breakeven_stop_prevents_loss(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 110.0}
        future = [
            {"timestamp": 1, "open": 100, "high": 105.5, "low": 100.1, "close": 104, "volume": 1000},
            {"timestamp": 2, "open": 104, "high": 104.2, "low": 99.7, "close": 100.3, "volume": 900},
        ]
        outcome = evaluate_signal_forward_outcome(
            signal=signal, future_klines=future, horizons=[2], exit_params={"breakeven_at_r": 1.0},
        )
        r = outcome["per_horizon_results"]["2"]
        assert r["breakeven_active"] is True
        assert r["hit_breakeven_stop"] is True
        assert r["realized_return_pct"] >= 0.0

    def test_trailing_stop_locks_profit(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 130.0}
        future = [
            {"timestamp": 1, "open": 100, "high": 106.0, "low": 100.2, "close": 105.8, "volume": 1000},
            {"timestamp": 2, "open": 105.8, "high": 109.5, "low": 105.0, "close": 108.8, "volume": 1000},
            {"timestamp": 3, "open": 108.8, "high": 109.0, "low": 106.0, "close": 106.5, "volume": 1000},
        ]
        outcome = evaluate_signal_forward_outcome(
            signal=signal, future_klines=future, horizons=[3],
            exit_params={"trail_at_r": 1.0, "trail_distance_r": 0.5},
        )
        r = outcome["per_horizon_results"]["3"]
        assert r["trailing_active"] is True
        assert r["hit_trailing_stop"] is True
        assert r["realized_r"] > 0.0

    def test_no_hit_uses_final_close(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 80.0, "take_profit": 200.0}
        future = _flat_klines(bars=5, price=101.0)
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[5])
        r = outcome["per_horizon_results"]["5"]
        assert r["first_hit"] == "none"
        assert r["hit_take_profit"] is False
        assert r["hit_stop_loss"] is False

    def test_insufficient_future_bars_warning(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        future = _flat_klines(bars=3, price=100.0)
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[10])
        assert "insufficient_future_bars:10" in outcome["warnings"]

    def test_short_side_mfe_mae_computation(self):
        signal = {"symbol": "BTCUSDT", "side": "SHORT", "entry_price": 100.0, "stop_loss": 105.0, "take_profit": 90.0}
        future = [
            {"timestamp": 1, "open": 100, "high": 100.5, "low": 97.0, "close": 98.0, "volume": 1000},
        ]
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[1])
        r = outcome["per_horizon_results"]["1"]
        assert r["max_favorable_excursion_pct"] > 0  # price went down = favorable for SHORT

    def test_custom_horizons_default(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        future = _flat_klines(bars=3, price=100.0)
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future)
        assert outcome["horizons"] == [5, 15, 30]

    def test_custom_horizons(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        future = _flat_klines(bars=3, price=100.0)
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[3, 7])
        assert outcome["horizons"] == [3, 7]

    def test_invalid_payload_warning(self):
        outcome = evaluate_signal_forward_outcome(signal={}, future_klines=[], horizons=[1])
        assert "invalid_signal_payload" in outcome["warnings"]

    def test_zero_entry_price_warning(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 0.0, "stop_loss": 95.0, "take_profit": 105.0}
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=[], horizons=[1])
        assert "missing_entry_price" in outcome["warnings"]

    def test_direction_field_as_side(self):
        signal = {"symbol": "ETHUSDT", "direction": "SELL", "entry_price": 200.0, "stop_loss": 210.0, "take_profit": 180.0}
        future = [{"timestamp": 1, "open": 200, "high": 200.1, "low": 179.5, "close": 181, "volume": 1000}]
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=future, horizons=[1])
        assert outcome["side"] == "SHORT"

    def test_signal_time_from_timestamp_field(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                  "take_profit": 105.0, "timestamp": "2024-01-15T08:00:00Z"}
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=[], horizons=[1])
        assert outcome["signal_time"] == "2024-01-15T08:00:00Z"


# ---------------------------------------------------------------------------
# summarize_outcomes_by_horizon
# ---------------------------------------------------------------------------

class TestSummarizeOutcomesByHorizon:
    def test_empty_returns_default_horizon_keys(self):
        result = summarize_outcomes_by_horizon(outcomes=[])
        assert set(result.keys()) == {"5", "15", "30"}
        for h in result.values():
            assert h["candidate_count"] == 0

    def test_basic(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        outcomes = [
            evaluate_signal_forward_outcome(signal=signal, future_klines=_trending_klines(bars=10), horizons=[5, 10]),
            evaluate_signal_forward_outcome(signal=signal, future_klines=_flat_klines(bars=10, price=99.0), horizons=[5, 10]),
        ]
        result = summarize_outcomes_by_horizon(outcomes=outcomes, horizons=[5, 10])
        assert "5" in result
        assert "10" in result
        for h in ["5", "10"]:
            assert result[h]["candidate_count"] == 2
            assert "avg_return_at_horizon" in result[h]
            assert "tp_hit_rate" in result[h]
            assert "sl_hit_rate" in result[h]

    def test_filters_non_dicts(self):
        outcomes: list[dict[str, Any]] = [{}, None, "bad", 123]  # type: ignore[list-item]
        result = summarize_outcomes_by_horizon(outcomes=outcomes)  # type: ignore[arg-type]
        for h in ["5", "15", "30"]:
            assert result[h]["candidate_count"] == 0


# ---------------------------------------------------------------------------
# summarize_outcomes_for_primary_horizon
# ---------------------------------------------------------------------------

class TestSummarizeOutcomesForPrimaryHorizon:
    def test_basic(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        outcomes = [
            evaluate_signal_forward_outcome(signal=signal, future_klines=_trending_klines(bars=10), horizons=[5]),
            evaluate_signal_forward_outcome(signal=signal, future_klines=_flat_klines(bars=10, price=99.0), horizons=[5]),
        ]
        summary = summarize_outcomes_for_primary_horizon(outcomes=outcomes, primary_horizon=5)
        assert summary["candidate_count"] == 2
        assert "expectancy_r" in summary
        assert "tp_hit_rate" in summary
        assert "sl_hit_rate" in summary

    def test_empty(self):
        summary = summarize_outcomes_for_primary_horizon(outcomes=[], primary_horizon=5)
        assert summary["candidate_count"] == 0

    def test_clamps_primary_horizon_to_min_1(self):
        summary = summarize_outcomes_for_primary_horizon(outcomes=[], primary_horizon=0)
        assert summary["candidate_count"] == 0


# ---------------------------------------------------------------------------
# summarize_outcomes_by_symbol
# ---------------------------------------------------------------------------

class TestSummarizeOutcomesBySymbol:
    def test_groups_and_sorts(self):
        signal_btc = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        signal_eth = {"symbol": "ETHUSDT", "side": "LONG", "entry_price": 200.0, "stop_loss": 190.0, "take_profit": 210.0}
        outcomes = [
            evaluate_signal_forward_outcome(signal=signal_btc, future_klines=_trending_klines(bars=10), horizons=[5]),
            evaluate_signal_forward_outcome(signal=signal_btc, future_klines=_trending_klines(bars=10), horizons=[5]),
            evaluate_signal_forward_outcome(signal=signal_eth, future_klines=_trending_klines(bars=10), horizons=[5]),
        ]
        rows = summarize_outcomes_by_symbol(outcomes=outcomes, primary_horizon=5)
        assert len(rows) >= 1
        symbols = {r["symbol"] for r in rows}
        assert "BTCUSDT" in symbols or "ETHUSDT" in symbols


# ---------------------------------------------------------------------------
# summarize_outcomes_by_time_bucket
# ---------------------------------------------------------------------------

class TestSummarizeOutcomesByTimeBucket:
    def test_buckets_by_day(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                  "take_profit": 105.0, "timestamp": 1704067200000}  # 2024-01-01
        outcomes = [
            evaluate_signal_forward_outcome(signal=signal, future_klines=_flat_klines(bars=10, price=100.0), horizons=[5]),
        ]
        rows = summarize_outcomes_by_time_bucket(outcomes=outcomes, primary_horizon=5)
        assert len(rows) >= 1
        assert "date" in rows[0]

    def test_empty(self):
        rows = summarize_outcomes_by_time_bucket(outcomes=[], primary_horizon=5)
        assert rows == []


# ---------------------------------------------------------------------------
# parse_shadow_order_plan
# ---------------------------------------------------------------------------

class TestParseShadowOrderPlan:
    def test_valid(self):
        plan = {
            "symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0,
            "stop_loss": 95.0, "take_profit": 105.0,
            "entry_timestamp_ms": 1704067200000,
        }
        result = parse_shadow_order_plan(plan)
        assert result["ok"] is True
        assert result["plan"]["symbol"] == "BTCUSDT"
        assert result["plan"]["side"] == "LONG"
        assert result["plan"]["entry_timestamp_ms"] == 1704067200000

    def test_valid_with_payload_wrapper(self):
        plan = {
            "payload": {
                "symbol": "ETHUSDT", "position_side": "SHORT", "entry_price": 200.0,
                "stop_loss": 210.0, "take_profit": 180.0,
                "timestamp": 1704067200000,
            }
        }
        result = parse_shadow_order_plan(plan)
        assert result["ok"] is True
        assert result["plan"]["symbol"] == "ETHUSDT"
        assert result["plan"]["side"] == "SHORT"

    def test_missing_symbol(self):
        result = parse_shadow_order_plan({"side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                                           "take_profit": 105.0, "entry_timestamp_ms": 1704067200000})
        assert result["ok"] is False
        assert result["error"] == "missing_required_field"

    def test_missing_timestamp(self):
        result = parse_shadow_order_plan({"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0,
                                           "stop_loss": 95.0, "take_profit": 105.0})
        assert result["ok"] is False
        assert result["error"] == "timestamp_parse_failed"

    def test_zero_entry_price(self):
        plan = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 0.0, "stop_loss": 95.0,
                "take_profit": 105.0, "entry_timestamp_ms": 1704067200000}
        result = parse_shadow_order_plan(plan)
        assert result["ok"] is False

    def test_not_dict(self):
        result = parse_shadow_order_plan("not_a_dict")  # type: ignore[arg-type]
        assert result["ok"] is False

    def test_iso_timestamp(self):
        plan = {
            "symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0,
            "stop_loss": 95.0, "take_profit": 105.0,
            "entry_timestamp": "2024-01-01T00:00:00Z",
        }
        result = parse_shadow_order_plan(plan)
        assert result["ok"] is True
        assert result["plan"]["entry_timestamp_ms"] == 1704067200000

    def test_seconds_timestamp_converted_to_ms(self):
        plan = {
            "symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0,
            "stop_loss": 95.0, "take_profit": 105.0,
            "entry_timestamp_ms": 1704067200,  # seconds
        }
        result = parse_shadow_order_plan(plan)
        assert result["ok"] is True
        assert result["plan"]["entry_timestamp_ms"] == 1704067200000

    def test_order_plan_status_preserved(self):
        plan = {
            "symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0,
            "stop_loss": 95.0, "take_profit": 105.0,
            "entry_timestamp_ms": 1704067200000,
            "order_plan_status": "pending",
        }
        result = parse_shadow_order_plan(plan)
        assert result["ok"] is True
        assert result["plan"]["order_plan_status"] == "pending"


# ---------------------------------------------------------------------------
# normalize_shadow_order_plan
# ---------------------------------------------------------------------------

class TestNormalizeShadowOrderPlan:
    def test_valid(self):
        plan = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                "take_profit": 105.0, "entry_timestamp_ms": 1704067200000}
        result = normalize_shadow_order_plan(plan)
        assert result is not None
        assert result["symbol"] == "BTCUSDT"

    def test_invalid_returns_none(self):
        result = normalize_shadow_order_plan({"symbol": "", "entry_price": 0})
        assert result is None


# ---------------------------------------------------------------------------
# dedupe_shadow_order_plans
# ---------------------------------------------------------------------------

class TestDedupeShadowOrderPlans:
    def test_removes_duplicates(self):
        plan = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                "take_profit": 105.0, "entry_timestamp_ms": 1704067200000}
        result = dedupe_shadow_order_plans([plan, plan, plan])
        assert len(result["unique_order_plans"]) == 1
        assert result["duplicates_removed"] == 2

    def test_counts_invalid(self):
        result = dedupe_shadow_order_plans([{"symbol": "", "entry_price": 0}])
        assert result["invalid_order_plans"] == 1

    def test_empty(self):
        result = dedupe_shadow_order_plans([])
        assert result["unique_order_plans"] == []
        assert result["duplicates_removed"] == 0


# ---------------------------------------------------------------------------
# build_shadow_order_outcome_rows
# ---------------------------------------------------------------------------

class TestBuildShadowOrderOutcomeRows:
    def test_basic(self):
        plan = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                "take_profit": 105.0, "entry_timestamp_ms": 1704067200000}
        future = _trending_klines(bars=20, start_price=100.0)
        rows = build_shadow_order_outcome_rows(order_plan=plan, future_klines=future, horizons=[5, 10])
        assert len(rows) == 2  # one per horizon
        for r in rows:
            assert r["symbol"] == "BTCUSDT"
            assert "exit_reason" in r
            assert "outcome_status" in r

    def test_invalid_plan_returns_empty(self):
        rows = build_shadow_order_outcome_rows(order_plan={"symbol": ""}, future_klines=[], horizons=[5])
        assert rows == []

    def test_filters_past_klines(self):
        plan = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                "take_profit": 105.0, "entry_timestamp_ms": 1704067200000}
        future = [
            {"timestamp": 1704066900000, "open": 99, "high": 99.5, "low": 98.5, "close": 99.3, "volume": 500},  # before
            {"timestamp": 1704067200000, "open": 100, "high": 100.1, "low": 99.9, "close": 100, "volume": 500},  # same ms
            {"timestamp": 1704067500000, "open": 100, "high": 106, "low": 99.8, "close": 105, "volume": 500},  # after
        ]
        rows = build_shadow_order_outcome_rows(order_plan=plan, future_klines=future, horizons=[5])
        assert len(rows) == 1

    def test_insufficient_future_bars_status(self):
        plan = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                "take_profit": 200.0, "entry_timestamp_ms": 1704067200000}
        future = _flat_klines(bars=3, price=100.0)
        rows = build_shadow_order_outcome_rows(order_plan=plan, future_klines=future, horizons=[10])
        assert len(rows) == 1
        assert rows[0]["outcome_status"] == "insufficient_future_bars"


# ---------------------------------------------------------------------------
# summarize_shadow_order_outcomes
# ---------------------------------------------------------------------------

class TestSummarizeShadowOrderOutcomes:
    def test_basic(self):
        plan = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
                "take_profit": 105.0, "entry_timestamp_ms": 1704067200000}
        future = _trending_klines(bars=20, start_price=100.0)
        rows = build_shadow_order_outcome_rows(order_plan=plan, future_klines=future, horizons=[5, 10])
        summary = summarize_shadow_order_outcomes(rows, total_orders=1)
        assert summary["total_orders"] == 1
        assert summary["unique_orders"] == 1
        assert summary["evaluated_orders"] == 1

    def test_empty(self):
        summary = summarize_shadow_order_outcomes([], total_orders=0)
        assert summary["total_orders"] == 0
        assert summary["unique_orders"] == 0

    def test_counts_open(self):
        plan = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 80.0,
                "take_profit": 200.0, "entry_timestamp_ms": 1704067200000}
        future = _flat_klines(bars=20, price=101.0)
        rows = build_shadow_order_outcome_rows(order_plan=plan, future_klines=future, horizons=[5, 10])
        summary = summarize_shadow_order_outcomes(rows, total_orders=1)
        assert summary["order_level_open_count"] == 1


# ---------------------------------------------------------------------------
# edge case: empty inputs across all public functions
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_evaluate_empty_future(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        outcome = evaluate_signal_forward_outcome(signal=signal, future_klines=[], horizons=[5])
        assert "insufficient_future_bars:5" in outcome["warnings"]

    def test_summarize_outcomes_by_horizon_custom_horizons(self):
        signal = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 105.0}
        outcomes = [evaluate_signal_forward_outcome(signal=signal, future_klines=_flat_klines(bars=10, price=100.0), horizons=[3, 7])]
        result = summarize_outcomes_by_horizon(outcomes=outcomes, horizons=[3, 7])
        assert "3" in result
        assert "7" in result

    def test_dedupe_different_prices_keeps_both(self):
        p1 = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "stop_loss": 95.0,
              "take_profit": 105.0, "entry_timestamp_ms": 1704067200000}
        p2 = {"symbol": "BTCUSDT", "side": "LONG", "entry_price": 101.0, "stop_loss": 96.0,
              "take_profit": 106.0, "entry_timestamp_ms": 1704067200000}
        result = dedupe_shadow_order_plans([p1, p2])
        assert len(result["unique_order_plans"]) == 2
