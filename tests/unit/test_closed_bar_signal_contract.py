"""P1-02 closed-bar selection, propagation and cohort contract tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from core.paper_trading.data_source import (
    CLOSED_BAR_CONTRACT_VERSION,
    MarketBar,
    select_closed_bars,
)
from core.paper_trading.paper_position import (
    OVERLAP_MANIFEST_FILENAME,
    build_overlap_exclusion_manifest,
    dict_to_position,
    load_canonical_closed_clean_positions,
    open_position,
    stable_signal_key,
)
from core.paper_trading.shadow_run_registry import build_run_record
from core.paper_trading.strategy_config import (
    AlertConfig,
    DataApiConfig,
    StrategyConfig,
    StrategyLibrary,
)
from core.paper_trading.strategy_registry import StrategyRunResult
from core.paper_trading.strategy_switchboard import run_switchboard
from core.paper_trading.trade_intent import build_trade_intent


UTC = timezone.utc
BASE = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


def _bar(index=0, timeframe="5m", close_time=None, close=100.0, **overrides):
    seconds = {"5m": 300, "15m": 900, "1h": 3600}[timeframe]
    opened = BASE + timedelta(seconds=index * seconds)
    value = {
        "timestamp": opened.timestamp(),
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": 10.0,
        "symbol": "BTCUSDT",
        "timeframe": timeframe,
        "close_time": close_time if close_time is not None else opened + timedelta(seconds=seconds),
    }
    value.update(overrides)
    return MarketBar(**value)


@pytest.mark.parametrize("timeframe", ["5m", "1h"])
def test_inclusive_boundary_and_multiple_timeframes(timeframe):
    bar = _bar(timeframe=timeframe)
    result = select_closed_bars([bar], bar.close_time)
    assert result.bars == [bar.__class__(**{**bar.__dict__, "provider_closed": True})]
    assert result.signal_bar_close_time.endswith("+00:00")
    assert result.contract_version == CLOSED_BAR_CONTRACT_VERSION


def test_forming_and_future_bars_are_excluded_before_use():
    closed = _bar(0)
    forming = _bar(1, close=999.0)
    result = select_closed_bars([closed, forming], closed.close_time)
    assert [bar.close for bar in result.bars] == [100.0]
    assert result.rejected_forming_or_future == 1


def test_missing_close_time_derives_only_from_declared_interval():
    derived = _bar(close_time=None)
    derived = MarketBar(**{**derived.__dict__, "close_time": None})
    result = select_closed_bars([derived], BASE + timedelta(minutes=5))
    assert result.eligible_count == 1
    ambiguous = MarketBar(**{**derived.__dict__, "timeframe": ""})
    rejected = select_closed_bars([ambiguous], BASE + timedelta(minutes=5))
    assert rejected.eligible_count == 0
    assert rejected.rejected_malformed == 1


def test_naive_and_inconsistent_close_times_fail_closed():
    naive = _bar(close_time=datetime(2026, 7, 20, 12, 5))
    inconsistent = _bar(close_time=BASE + timedelta(hours=2))
    result = select_closed_bars([naive, inconsistent], BASE + timedelta(hours=3))
    assert result.eligible_count == 0
    assert result.rejected_malformed == 2


def test_ordering_identical_dedup_and_conflicting_duplicate_rejection():
    first = _bar(0)
    second = _bar(1)
    ordered = select_closed_bars(
        [second, first, first], second.close_time,
    )
    assert [bar.timestamp for bar in ordered.bars] == [first.timestamp, second.timestamp]
    conflicting = MarketBar(**{**first.__dict__, "close": 101.0, "high": 102.0})
    rejected = select_closed_bars([first, conflicting, second], second.close_time)
    assert [bar.timestamp for bar in rejected.bars] == [second.timestamp]
    assert rejected.rejected_conflicting_duplicate == 1


def _library():
    api = DataApiConfig(
        name="public", api_type="binance_public_klines", market="usdm",
        readonly=True, requires_secret=False, allows_orders=False, default_limit=120,
    )
    strategy = StrategyConfig(
        strategy_id="macd_rebound_watch", strategy_type="macd_rebound_watch",
        description="test", enabled=True, data_api="public", symbols=["BTCUSDT"],
        timeframes=["5m"], mode="paper",
        alert=AlertConfig(feishu_payload=True, auto_send=False),
    )
    return StrategyLibrary(
        version=1, default_mode="paper", default_alert="payload",
        data_apis={"public": api}, strategies={strategy.strategy_id: strategy},
        enabled_strategies={strategy.strategy_id: strategy}, disabled_strategies={},
    )


class _Adapter:
    def __init__(self, bars):
        self.bars = bars

    def get_bars(self, _symbol, timeframe="1h", limit=100):
        return self.bars[:limit]


def test_switchboard_filters_before_indicator_calculation(monkeypatch):
    bars = [_bar(i) for i in range(30)]
    forming = _bar(30, close=10000.0)
    captured = {}

    def fake_analyze(strategy_id, strategy_type, selected, **kwargs):
        captured["bars"] = selected
        captured.update(kwargs)
        return StrategyRunResult(
            strategy_id=strategy_id, strategy_type=strategy_type,
            symbol="BTCUSDT", timeframe="5m", success=True,
            candidate=None, error=None,
        )

    monkeypatch.setattr("core.paper_trading.strategy_switchboard.analyze_for_strategy", fake_analyze)
    monkeypatch.setattr("core.paper_trading.strategy_switchboard.time.sleep", lambda _x: None)
    result = run_switchboard(
        _library(), _Adapter(bars + [forming]), "2026-07-20",
        decision_cutoff=bars[-1].close_time,
    )
    assert len(captured["bars"]) == 30
    assert captured["bars"][-1].close == 100.0
    assert captured["signal_bar_close_time"] == result.closed_bar_audits[0]["signal_bar_close_time"]
    assert result.closed_bar_audits[0]["rejected_forming_or_future"] == 1


def _plan(signal_close="2026-07-20T12:05:00.000+00:00"):
    return {
        "direction": "LONG_OBSERVE",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "entry_observation": 100.0,
        "invalidation_level": 95.0,
        "take_profit_observation": 110.0,
        "rr_ratio": 2.0,
        "risk_distance_pct": 5.0,
        "reward_distance_pct": 10.0,
        "reason": "macd_rebound_watch: test",
        "signal_bar_close_time": signal_close,
        "signal_bar_contract_version": CLOSED_BAR_CONTRACT_VERSION,
    }


def test_same_closed_bar_identity_stable_and_next_bar_different():
    first = build_trade_intent(_plan(), "2026-07-20").to_dict()
    retry = build_trade_intent(_plan(), "2026-07-20").to_dict()
    next_bar = build_trade_intent(
        _plan("2026-07-20T12:10:00.000+00:00"), "2026-07-20"
    ).to_dict()
    assert stable_signal_key(first) == stable_signal_key(retry)
    assert stable_signal_key(first) != stable_signal_key(next_bar)


def test_open_ledger_round_trip_preserves_closed_bar_contract():
    intent = build_trade_intent(_plan(), "2026-07-20").to_dict()
    position = open_position(intent)
    assert position is not None
    restored = dict_to_position(json.loads(json.dumps(position.to_dict())))
    assert restored.signal_bar_close_time == "2026-07-20T12:05:00.000+00:00"
    assert restored.signal_bar_contract_version == CLOSED_BAR_CONTRACT_VERSION
    assert restored.signal_key == stable_signal_key(intent)


def test_open_rejects_future_or_incomplete_closed_bar_contract():
    future = build_trade_intent(
        _plan("2099-07-20T12:05:00.000+00:00"), "2026-07-20"
    ).to_dict()
    assert open_position(future) is None
    missing = build_trade_intent(_plan(), "2026-07-20").to_dict()
    missing["signal_bar_close_time"] = None
    assert open_position(missing) is None


def test_legacy_and_p1_02_trusted_cohorts_remain_distinct(tmp_path):
    trusted = open_position(build_trade_intent(_plan(), "2026-07-20").to_dict()).to_dict()
    trusted.update({
        "position_id": "P_TRUSTED", "opened_at": "2026-07-20T12:06:00+00:00",
        "created_at": "2026-07-20T12:06:00+00:00", "recorded_at": "2026-07-20T12:07:00+00:00",
        "status": "TAKE_PROFIT_HIT", "closed_at": "2026-07-20T12:07:00+00:00",
        "exit_price": 110.0, "r_multiple": 2.0, "quarantine_status": "CLEAN",
    })
    legacy = dict(trusted)
    legacy.update({
        "position_id": "P_LEGACY", "intent_id": "TI_LEGACY", "symbol": "ETHUSDT",
        "signal_bar_close_time": None, "signal_bar_contract_version": "legacy_missing",
        "opened_at": "2026-07-20T12:08:00+00:00", "created_at": "2026-07-20T12:08:00+00:00",
        "recorded_at": "2026-07-20T12:09:00+00:00", "closed_at": "2026-07-20T12:09:00+00:00",
    })
    records = [trusted, legacy]
    (tmp_path / "2026-07-20_paper_position_ledger.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in records)
    )
    (tmp_path / "2026-07-20_shadow_lifecycle_result.json").write_text(json.dumps({
        "date": "2026-07-20", "mode": "real_public_readonly",
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }))
    manifest = build_overlap_exclusion_manifest(records, "2026-07-20T12:00:00+00:00")
    manifest["closed_bar_trusted_cohort_start_at"] = "2026-07-20T12:05:30+00:00"
    manifest["closed_bar_trusted_cohort_rule_version"] = CLOSED_BAR_CONTRACT_VERSION
    (tmp_path / OVERLAP_MANIFEST_FILENAME).write_text(json.dumps(manifest))
    eligible, _all, diag = load_canonical_closed_clean_positions(str(tmp_path))
    assert len(eligible) == 2
    assert diag["trusted_cohort_closed"] == 2
    assert diag["p1_02_trusted_cohort_closed"] == 1
    assert diag["legacy_closed_without_closed_bar_contract"] == 1


def test_p1_02_cohort_is_not_locally_activated(tmp_path):
    manifest = build_overlap_exclusion_manifest([], "2026-07-20T12:00:00+00:00")
    (tmp_path / OVERLAP_MANIFEST_FILENAME).write_text(json.dumps(manifest))
    _eligible, _all, diag = load_canonical_closed_clean_positions(str(tmp_path))
    assert diag["p1_02_trusted_cohort_start_at"] is None
    assert diag["p1_02_trusted_cohort_closed"] == 0


def test_accepted_overlap_fixture_remains_exactly_200():
    positions = []
    for index in range(201):
        opened = BASE + timedelta(seconds=index)
        positions.append({
            "position_id": f"P{index}", "strategy_id": "macd_rebound_watch",
            "symbol": "BTCUSDT", "timeframe": "5m", "side": "LONG",
            "opened_at": opened.isoformat(),
            "closed_at": (BASE + timedelta(hours=1)).isoformat(),
        })
    manifest = build_overlap_exclusion_manifest(
        positions, "2026-07-20T14:00:00+00:00"
    )
    assert manifest["excluded_overlap_positions"] == 200


def test_run_registry_propagates_closed_bar_summary():
    record = build_run_record({
        "date": "2026-07-20", "mode": "real_public_readonly",
        "pipeline_status": "PASS", "summary": {
            "closed_bar_contract_version": CLOSED_BAR_CONTRACT_VERSION,
            "decision_cutoff": "2026-07-20T12:00:00.000+00:00",
            "closed_bar_counts": {"raw_candles": 120, "eligible_closed_candles": 119},
        }, "safety_flags": ["SHADOW_ONLY", "NO_TESTNET", "NO_LIVE"],
    }, run_id="RUN")
    data = record.to_dict()
    assert data["closed_bar_contract_version"] == CLOSED_BAR_CONTRACT_VERSION
    assert data["decision_cutoff"].endswith("+00:00")
    assert data["closed_bar_counts"]["eligible_closed_candles"] == 119
    assert "NO_TESTNET" in data["safety_flags"] and "NO_LIVE" in data["safety_flags"]
