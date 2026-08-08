"""P1-03 prospective funding lifecycle — integration tests.

Tests the real production path: positions closed by the simulator
automatically receive funding evidence via enrich_closed_position_funding().
No手工塞字段.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from core.paper_trading.net_friction import (
    FRICTION_MODEL_VERSION,
    assess_position_friction,
    aggregate_net_metrics,
)
from core.paper_trading.paper_position_simulator import (
    _update_position,
    _adapter_events_to_evidence,
    enrich_closed_position_funding,
)
from core.paper_trading.paper_position import PaperPosition


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------

@dataclass
class MockBar:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 1000.0
    timeframe: str = "5m"
    close_time: str = "2026-07-21T04:05:00+00:00"


class MockFundingAdapter:
    """Mock adapter that returns predefined funding events."""

    def __init__(self, events: list[dict[str, Any]] | None = None,
                 fail: bool = False):
        self._events = events or []
        self._fail = fail
        self.call_count = 0

    def get_funding_events(self, symbol: str, lookback_seconds: int) -> list[dict]:
        self.call_count += 1
        if self._fail:
            raise ConnectionError("adapter unavailable")
        return [e for e in self._events if e.get("symbol") == symbol]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_position(**overrides) -> PaperPosition:
    defaults = {
        "position_id": "PP_test_001",
        "intent_id": "INT_test_001",
        "signal_key": "sig-test",
        "signal_key_schema_version": "v1",
        "date": "2026-07-21",
        "source": "test",
        "strategy_id": "weak_short_watch",
        "strategy_type": "weak_short",
        "symbol": "XRPUSDT",
        "timeframe": "5m",
        "side": "SHORT",
        "status": "OPEN",
        "entry_price": 2.50,
        "stop_loss": 2.60,
        "take_profit": 2.40,
        "rr_ratio": 1.0,
        "position_size_preview": 300.0,
        "max_risk_pct": 1.0,
        "paper_equity_preview": 10000.0,
        "opened_at": "2026-07-21T00:00:00+00:00",
        "opened_bar_time": 1784592000,
        "closed_at": "2026-07-21T04:00:00+00:00",
        "exit_price": None,
        "exit_reason": None,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "realized_pnl_pct": 0.0,
        "r_multiple": 0.0,
        "source_trade_intent_status": "SHADOW_READY",
        "risk_gate_status": "PASS",
        "lifecycle_mode": "future_only",
        "last_checked_at": None,
        "last_checked_bar_time": None,
        "safety_flags": [],
        "created_at": "2026-07-21T00:00:00+00:00",
        "signal_bar_contract_version": "closed_bar_v1",
    }
    defaults.update(overrides)
    return PaperPosition(**defaults)


def _tp_bar() -> MockBar:
    """Bar that triggers SHORT TP (low <= 2.40)."""
    return MockBar(timestamp=1784606400.0, open=2.48, high=2.49, low=2.39, close=2.42)


def _sl_bar_no_gap() -> MockBar:
    """Bar that triggers SHORT SL without gap (high >= 2.60, open < 2.60)."""
    return MockBar(timestamp=1784606400.0, open=2.55, high=2.61, low=2.54, close=2.58)


def _sl_bar_gap() -> MockBar:
    """Bar that triggers SHORT SL with gap (open > 2.60)."""
    return MockBar(timestamp=1784606400.0, open=2.65, high=2.66, low=2.63, close=2.64)


def _timeout_bar() -> MockBar:
    """Bar that doesn't trigger TP or SL — will timeout."""
    return MockBar(timestamp=1784606400.0, open=2.48, high=2.49, low=2.47, close=2.48)


def _funding_event(
    symbol: str = "XRPUSDT",
    event_at: str = "2026-07-21T02:00:00+00:00",
    rate: str = "0.0001",
    mark: str = "2.45",
) -> dict:
    return {
        "symbol": symbol,
        "funding_event_at": event_at,
        "signed_funding_rate": rate,
        "mark_price": mark,
        "funding_interval_seconds": 28800,
        "source": "binance_usdm_public",
        "source_event_identity": f"{symbol}:{event_at}",
    }


def _assumptions() -> dict:
    return {
        "friction_model_version": FRICTION_MODEL_VERSION,
        "quote_currency": "USDT",
        "active_symbol_mapping": {
            "XRPUSDT": {"profile": "DEFAULT", "venue": "binance", "instrument_type": "linear_perpetual"},
        },
        "profiles": {
            "DEFAULT": {
                "entry_fee_bps": "5", "exit_fee_bps": "5",
                "entry_fee_liquidity": "TAKER", "exit_fee_liquidity": "TAKER",
                "fee_rate_source": "test_fixture",
                "entry_spread_bps": "0.5", "exit_spread_bps": "0.5",
                "entry_slippage_bps": "0", "exit_slippage_bps": "0",
                "spread_input_semantics": "ONE_LEG_ADVERSE_BPS",
                "slippage_source": "CONFIGURED_ESTIMATE",
                "funding_mode": "OBSERVED_EVENTS",
                "gap_execution_mode": "OBSERVED_FIRST_EXECUTABLE",
                "maximum_supported_notional_quote": "1000",
                "maximum_supported_notional_currency": "USDT",
                "notional_measurement_version": "entry_exit_max_v1",
            },
        },
    }


# ---------------------------------------------------------------------------
# CASE A: Bracketing events + event inside window + TP → COMPLETE
# ---------------------------------------------------------------------------
def test_case_a_no_funding_tp():
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T02:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])
    pos = _make_position()
    bars = [_tp_bar()]
    result = _update_position(pos, bars, timeout_bars=24, adapter=adapter)

    assert result["status"] == "TAKE_PROFIT_HIT"
    assert len(result.get("funding_events", [])) == 1
    assert result.get("funding_events_verified_complete") is True

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "COMPLETE_ESTIMATED", assessment.get("errors")
    assert assessment["net_pnl_quote"] is not None
    assert assessment["net_r"] is not None
    assert Decimal(assessment["funding_effect_r"]) != 0


# ---------------------------------------------------------------------------
# CASE B: Bracketing events + TP → COMPLETE
# ---------------------------------------------------------------------------
def test_case_b_funding_tp():
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T02:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])
    pos = _make_position()
    bars = [_tp_bar()]
    result = _update_position(pos, bars, timeout_bars=24, adapter=adapter)

    assert result["status"] == "TAKE_PROFIT_HIT"
    assert len(result.get("funding_events", [])) == 1
    assert result["funding_events_verified_complete"] is True

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "COMPLETE_ESTIMATED", assessment.get("errors")
    assert assessment["net_pnl_quote"] is not None
    assert assessment["net_r"] is not None
    assert Decimal(assessment["funding_effect_r"]) != 0


# ---------------------------------------------------------------------------
# CASE C: Normal stop (no gap) + bracketing → COMPLETE
# ---------------------------------------------------------------------------
def test_case_c_normal_stop():
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T02:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])
    pos = _make_position()
    bars = [_sl_bar_no_gap()]
    result = _update_position(pos, bars, timeout_bars=24, adapter=adapter)

    assert result["status"] == "STOP_LOSS_HIT"
    assert result.get("funding_events_verified_complete") is True
    assert result.get("gap_execution_evidence_version") == "stop_trigger_bar_open_v1"

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "COMPLETE_ESTIMATED", assessment.get("errors")
    assert assessment["net_pnl_quote"] is not None
    assert assessment["net_r"] is not None


# ---------------------------------------------------------------------------
# CASE D: Gap-through stop + bracketing → COMPLETE
# ---------------------------------------------------------------------------
def test_case_d_gap_stop():
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T02:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])
    pos = _make_position()
    bars = [_sl_bar_gap()]
    result = _update_position(pos, bars, timeout_bars=24, adapter=adapter)

    assert result["status"] == "STOP_LOSS_HIT"
    assert result.get("funding_events_verified_complete") is True
    assert result.get("gap_execution_reference_price") == 2.65

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "COMPLETE_ESTIMATED", assessment.get("errors")
    assert assessment["net_pnl_quote"] is not None
    assert assessment["net_r"] is not None
    assert Decimal(assessment["gap_execution_effect_r"]) < 0


# ---------------------------------------------------------------------------
# CASE E: Timeout + bracketing → COMPLETE
# ---------------------------------------------------------------------------
def test_case_e_timeout():
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T02:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])
    pos = _make_position()
    bars = [_timeout_bar()]
    result = _update_position(pos, bars, timeout_bars=0, adapter=adapter)

    assert result["status"] == "TIMEOUT_EXIT"
    assert result.get("funding_events_verified_complete") is True

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "COMPLETE_ESTIMATED", assessment.get("errors")
    assert assessment["net_pnl_quote"] is not None
    assert assessment["net_r"] is not None


# ---------------------------------------------------------------------------
# CASE F: Missing funding evidence (adapter fails) → PARTIAL
# ---------------------------------------------------------------------------
def test_case_f_missing_funding_evidence():
    adapter = MockFundingAdapter(fail=True)
    pos = _make_position()
    bars = [_tp_bar()]
    result = _update_position(pos, bars, timeout_bars=24, adapter=adapter)

    assert result["status"] == "TAKE_PROFIT_HIT"
    assert result.get("funding_events") == []
    assert result.get("funding_events_verified_complete") is False

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "PARTIAL"
    assert assessment["net_r"] is None


# ---------------------------------------------------------------------------
# No adapter → position has no funding fields (backward compatible)
# ---------------------------------------------------------------------------
def test_no_adapter_backward_compatible():
    pos = _make_position()
    bars = [_tp_bar()]
    result = _update_position(pos, bars, timeout_bars=24, adapter=None)

    assert result["status"] == "TAKE_PROFIT_HIT"
    assert "funding_events" not in result
    assert "funding_events_verified_complete" not in result


# ---------------------------------------------------------------------------
# Funding replay idempotency
# ---------------------------------------------------------------------------
def test_funding_replay_idempotent():
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T02:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])

    pos = _make_position()
    bars = [_tp_bar()]

    result1 = _update_position(pos, bars, timeout_bars=24, adapter=adapter)
    result2 = _update_position(pos, bars, timeout_bars=24, adapter=adapter)

    assert result1["funding_events"] == result2["funding_events"]
    assert result1["funding_events_verified_complete"] == result2["funding_events_verified_complete"]
    assert adapter.call_count == 2


# ---------------------------------------------------------------------------
# enrich_closed_position_funding — direct test
# ---------------------------------------------------------------------------
def test_enrich_direct_no_events():
    """Adapter returns [] → no events → continuity cannot be proven → PARTIAL."""
    adapter = MockFundingAdapter(events=[])
    pos = {
        "position_id": "PP_x", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T00:00:00+00:00",
        "closed_at": "2026-07-21T09:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert result["funding_events"] == []
    assert result["funding_events_verified_complete"] is False


# ---------------------------------------------------------------------------
# Empty adapter → PARTIAL (no events = no continuity proof)
# ---------------------------------------------------------------------------
def test_empty_adapter_returns_partial():
    """Adapter returns [] → zero events → verified_complete=false → PARTIAL."""
    adapter = MockFundingAdapter(events=[])
    pos = {
        "position_id": "PP_empty", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T00:00:00+00:00",
        "closed_at": "2026-07-21T04:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
        "exit_price": 2.40, "realized_pnl": 30.0, "r_multiple": 1.0,
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert result["funding_events"] == []
    assert result["funding_events_verified_complete"] is False

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "PARTIAL"
    assert assessment["net_r"] is None


# ---------------------------------------------------------------------------
# Surrounding windows → PARTIAL (events only after close, no bracket)
# ---------------------------------------------------------------------------
def test_surrounding_windows_complete():
    """Position lifetime has no funding events, events only after close.
    With strict bracketing, this is AFTER_ONLY → PARTIAL."""
    event_after_1 = _funding_event(event_at="2026-07-21T04:30:00+00:00")
    event_after_2 = _funding_event(event_at="2026-07-21T12:30:00+00:00")
    adapter = MockFundingAdapter(events=[event_after_1, event_after_2])
    pos = {
        "position_id": "PP_surround", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T00:00:00+00:00",
        "closed_at": "2026-07-21T04:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
        "exit_price": 2.40, "realized_pnl": 30.0, "r_multiple": 1.0,
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert result["funding_events"] == []
    assert result["funding_events_verified_complete"] is False

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "PARTIAL"
    assert assessment["net_r"] is None


# ---------------------------------------------------------------------------
# CASE 2: AFTER_ONLY → PARTIAL (events only after close, no bracket)
# ---------------------------------------------------------------------------
def test_after_only_case():
    """Position 00:00→04:00, events 04:30/12:30 → AFTER_ONLY → PARTIAL."""
    event_after_1 = _funding_event(event_at="2026-07-21T04:30:00+00:00")
    event_after_2 = _funding_event(event_at="2026-07-21T12:30:00+00:00")
    adapter = MockFundingAdapter(events=[event_after_1, event_after_2])
    pos = {
        "position_id": "PP_after_only", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T00:00:00+00:00",
        "closed_at": "2026-07-21T04:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
        "exit_price": 2.40, "realized_pnl": 30.0, "r_multiple": 1.0,
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert result["funding_events"] == []
    assert result["funding_events_verified_complete"] is False

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "PARTIAL"
    assert assessment["net_r"] is None


# ---------------------------------------------------------------------------
# CASE 3: BEFORE_ONLY → PARTIAL (events only before open, no bracket)
# ---------------------------------------------------------------------------
def test_before_only_case():
    """Position 08:00→12:00, events 00:00/04:00 → BEFORE_ONLY → PARTIAL."""
    event_before_1 = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_before_2 = _funding_event(event_at="2026-07-21T04:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before_1, event_before_2])
    pos = {
        "position_id": "PP_before_only", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T08:00:00+00:00",
        "closed_at": "2026-07-21T12:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
        "exit_price": 2.40, "realized_pnl": 30.0, "r_multiple": 1.0,
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert result["funding_events"] == []
    assert result["funding_events_verified_complete"] is False

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "PARTIAL"
    assert assessment["net_r"] is None


# ---------------------------------------------------------------------------
# CASE 4: TRUE_SURROUNDING → COMPLETE (events bracket position, continuous)
# ---------------------------------------------------------------------------
def test_true_surrounding_case():
    """Position 01:00→04:00, events 00:00/08:00 → TRUE_SURROUNDING → COMPLETE."""
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_after])
    pos = {
        "position_id": "PP_true_surround", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T01:00:00+00:00",
        "closed_at": "2026-07-21T04:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
        "exit_price": 2.40, "realized_pnl": 30.0, "r_multiple": 1.0,
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert result["funding_events"] == []
    assert result["funding_events_verified_complete"] is True

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "COMPLETE_ESTIMATED"
    assert assessment["net_r"] is not None


# ---------------------------------------------------------------------------
# CASE 5: CROSS_FUNDING → COMPLETE (events bracket + event inside window)
# ---------------------------------------------------------------------------
def test_cross_funding_case():
    """Position 01:00→12:00, events 00:00/08:00/16:00 → CROSS_FUNDING → COMPLETE.
    The 08:00 event falls inside the position window and is correctly attributed."""
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T16:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])
    pos = {
        "position_id": "PP_cross_funding", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T01:00:00+00:00",
        "closed_at": "2026-07-21T12:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
        "exit_price": 2.40, "realized_pnl": 30.0, "r_multiple": 1.0,
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert len(result["funding_events"]) == 1
    assert result["funding_events"][0]["funding_timestamp"] == "2026-07-21T08:00:00+00:00"
    assert result["funding_events_verified_complete"] is True

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "COMPLETE_ESTIMATED"
    assert assessment["net_r"] is not None
    assert Decimal(assessment["funding_effect_r"]) != 0


def test_enrich_direct_with_events():
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T02:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])
    pos = {
        "position_id": "PP_x", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T00:00:00+00:00",
        "closed_at": "2026-07-21T09:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
    }
    result = enrich_closed_position_funding(
        pos, adapter, bar_close_time="2026-07-21T04:05:00+00:00",
    )
    assert len(result["funding_events"]) == 1
    assert result["funding_events_verified_complete"] is True


def test_enrich_direct_adapter_fail():
    adapter = MockFundingAdapter(fail=True)
    pos = {
        "position_id": "PP_x", "symbol": "XRPUSDT", "side": "SHORT",
        "entry_price": 2.50, "stop_loss": 2.60, "position_size_preview": 300.0,
        "opened_at": "2026-07-21T00:00:00+00:00",
        "closed_at": "2026-07-21T09:00:00+00:00",
        "status": "TAKE_PROFIT_HIT",
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert result["funding_events"] == []
    assert result["funding_events_verified_complete"] is False


def test_enrich_skips_open_position():
    adapter = MockFundingAdapter(events=[])
    pos = {
        "position_id": "PP_x", "symbol": "XRPUSDT", "side": "SHORT",
        "status": "OPEN",
    }
    result = enrich_closed_position_funding(pos, adapter)
    assert "funding_events" not in result


# ---------------------------------------------------------------------------
# Adapter events to evidence conversion
# ---------------------------------------------------------------------------
def test_adapter_events_to_evidence():
    raw = [_funding_event()]
    evidence = _adapter_events_to_evidence(raw)
    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "FUNDING_EVENT"
    assert evidence[0]["exchange_event_at"] == "2026-07-21T02:00:00+00:00"
    assert "evidence_id" in evidence[0]


# ---------------------------------------------------------------------------
# CASE G: Successful HTTP but funding events outside position window → PARTIAL
# ---------------------------------------------------------------------------
def test_case_g_missing_funding_window():
    """Adapter succeeds but events fall outside position lifetime → PARTIAL."""
    event_outside = _funding_event(event_at="2026-07-21T14:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_outside])
    pos = _make_position(closed_at="2026-07-21T03:00:00+00:00")
    bars = [_tp_bar()]
    result = _update_position(pos, bars, timeout_bars=24, adapter=adapter)

    assert result["status"] == "TAKE_PROFIT_HIT"
    assert result.get("funding_events") == []
    assert result.get("funding_events_verified_complete") is False

    assessment = assess_position_friction(result, _assumptions())
    assert assessment["friction_model_status"] == "PARTIAL"
    assert assessment["net_r"] is None


# ---------------------------------------------------------------------------
# CASE H: Real runner passes adapter into simulator
# ---------------------------------------------------------------------------
def test_case_h_runner_passes_adapter(monkeypatch):
    """Regression: run_paper_position_simulator.py threads adapter to simulator."""
    import sys
    import tempfile
    import json
    import os

    class SpyAdapter:
        def get_bars(self, symbol, timeframe="5m", limit=60):
            return []
        def get_funding_events(self, symbol, lookback_seconds):
            return []

    spy = SpyAdapter()
    captured_adapter = {}

    monkeypatch.setattr(
        "scripts.run_paper_position_simulator.BinancePublicKlineAdapter",
        lambda config: spy,
    )

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    import scripts.run_paper_position_simulator as runner_mod
    original_update_only = runner_mod.simulate_existing_positions_update_only

    def capturing_update_only(existing, bars, date_str, **kwargs):
        captured_adapter["adapter"] = kwargs.get("adapter")
        return original_update_only(existing, bars, date_str, **kwargs)

    monkeypatch.setattr(runner_mod, "simulate_existing_positions_update_only", capturing_update_only)
    runner_main = runner_mod.main
    sys.path.pop(0)

    with tempfile.TemporaryDirectory() as tmpdir:
        intents_path = os.path.join(tmpdir, "2026-07-21_trade_intents.json")
        existing_pos = {
            "position_id": "PP_runner_001", "intent_id": "INT_runner_001",
            "signal_key": "sig-runner", "signal_key_schema_version": "v1",
            "date": "2026-07-21", "source": "test",
            "strategy_id": "weak_short_watch", "strategy_type": "weak_short",
            "symbol": "XRPUSDT", "timeframe": "5m", "side": "SHORT",
            "status": "OPEN", "entry_price": 2.50, "stop_loss": 2.60,
            "take_profit": 2.40, "rr_ratio": 1.0,
            "position_size_preview": 300.0, "max_risk_pct": 1.0,
            "paper_equity_preview": 10000.0,
            "opened_at": "2026-07-21T00:00:00+00:00",
            "opened_bar_time": 1784592000,
            "closed_at": None, "exit_price": None, "exit_reason": None,
            "unrealized_pnl": 0.0, "realized_pnl": 0.0,
            "realized_pnl_pct": 0.0, "r_multiple": 0.0,
            "source_trade_intent_status": "SHADOW_READY",
            "risk_gate_status": "PASS", "lifecycle_mode": "future_only",
            "last_checked_at": None, "last_checked_bar_time": None,
            "safety_flags": [], "created_at": "2026-07-21T00:00:00+00:00",
            "signal_bar_contract_version": "closed_bar_v1",
        }
        with open(intents_path, "w") as f:
            json.dump({"intents": []}, f)
        existing_path = os.path.join(tmpdir, "2026-07-21_paper_positions.json")
        with open(existing_path, "w") as f:
            json.dump({"positions": [existing_pos]}, f)

        monkeypatch.setattr(sys, "argv", [
            "run_paper_position_simulator.py",
            "--date", "2026-07-21",
            "--input-file", intents_path,
            "--output-dir", tmpdir,
            "--allow-public-http",
            "--update-with-klines",
            "--update-existing-only",
        ])
        rc = runner_main()

    assert rc == 0
    assert captured_adapter.get("adapter") is spy


# ---------------------------------------------------------------------------
# Aggregate: all5 COMPLETE cases together
# ---------------------------------------------------------------------------
def test_aggregate_all_complete_cases():
    event_before = _funding_event(event_at="2026-07-21T00:00:00+00:00")
    event_inside = _funding_event(event_at="2026-07-21T02:00:00+00:00")
    event_after = _funding_event(event_at="2026-07-21T08:00:00+00:00")
    adapter = MockFundingAdapter(events=[event_before, event_inside, event_after])
    assumptions = _assumptions()
    assessments = []

    for bars, status in [
        ([_tp_bar()], "TP"),
        ([_sl_bar_no_gap()], "SL normal"),
        ([_sl_bar_gap()], "SL gap"),
        ([_timeout_bar()], "timeout"),
    ]:
        timeout = 0 if status == "timeout" else 24
        pos = _make_position()
        result = _update_position(pos, bars, timeout_bars=timeout, adapter=adapter)
        a = assess_position_friction(result, assumptions)
        assert a["friction_model_status"] == "COMPLETE_ESTIMATED", f"{status}: {a.get('errors')}"
        assessments.append(a)

    agg = aggregate_net_metrics(assessments)
    assert agg["net_metrics_status"] == "COMPLETE_ESTIMATED"
    assert agg["net_profit_factor"] is not None
    assert agg["net_expectancy_r"] is not None
    assert agg["net_coverage_ratio"] == "1"
