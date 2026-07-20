"""P1-01 cross-day exposure identity and legacy exclusion regression tests."""
from __future__ import annotations

import json

import pytest

from core.paper_trading.paper_position import (
    OVERLAP_MANIFEST_FILENAME,
    build_overlap_exclusion_manifest,
    exposure_identity,
    load_canonical_closed_clean_positions,
    stable_signal_key,
)
from core.paper_trading.paper_position_simulator import simulate_intent_only
from scripts.run_paper_position_simulator import _load_entry_guard_state
from scripts.run_shadow_trading_lifecycle import _build_steps


def _intent(**overrides):
    value = {
        "intent_id": "TI_DAY2",
        "date": "2026-07-20",
        "strategy_id": "macd_rebound_watch",
        "strategy_type": "macd_rebound_watch",
        "strategy_version": "1",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "side": "LONG",
        "intent_status": "SHADOW_READY",
        "execution_mode": "shadow_only",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "rr_ratio": 2.0,
        "position_size_preview": 1.0,
        "max_risk_pct": 0.5,
        "risk_gate_status": "PASS",
        "signal_bar_close_time": "2026-07-20T01:00:00+00:00",
    }
    value.update(overrides)
    return value


def _position(position_id, opened_at, status="OPEN", **overrides):
    value = {
        "position_id": position_id,
        "intent_id": f"TI_{position_id}",
        "date": opened_at[:10],
        "source": "trade_intent",
        "strategy_id": "macd_rebound_watch",
        "strategy_type": "macd_rebound_watch",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "side": "LONG",
        "status": status,
        "opened_at": opened_at,
        "created_at": opened_at,
        "recorded_at": opened_at,
        "closed_at": None,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "exit_price": None,
        "r_multiple": 0.0,
        "lifecycle_mode": "future_only",
    }
    value.update(overrides)
    return value


def _write_ledger(path, records):
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def test_cross_day_canonical_open_is_loaded_before_new_entry(tmp_path):
    old = _position("P_DAY1", "2026-07-19T00:00:00+00:00")
    _write_ledger(tmp_path / "2026-07-19_paper_position_ledger.jsonl", [old])
    (tmp_path / "2026-07-20_paper_positions.json").write_text('{"positions": []}')

    opens, _all, signal_keys, diag = _load_entry_guard_state(
        str(tmp_path), "2026-07-20",
    )
    result = simulate_intent_only(
        [_intent()], "2026-07-20", opens, existing_signal_keys=signal_keys,
    )

    assert diag["canonical_open_count_before_new_entries"] == 1
    assert result.lifecycle_stats["new_positions_count"] == 0
    assert result.lifecycle_stats["positions_skipped_overlap_open"] == 1
    detail = result.lifecycle_stats["skipped_overlap_intents"][0]
    assert detail["reason"] == "existing_open_exposure"
    assert detail["existing_position_id"] == "P_DAY1"


def test_same_signal_double_run_is_idempotent():
    first = simulate_intent_only([_intent()], "2026-07-20")
    second = simulate_intent_only(
        [_intent(intent_id="TI_RANDOM_RETRY")], "2026-07-20", first.positions,
    )
    assert first.lifecycle_stats["new_positions_count"] == 1
    assert second.lifecycle_stats["new_positions_count"] == 0
    assert second.lifecycle_stats["positions_skipped_overlap_open"] == 1
    assert second.open_count == 1


def test_cloud_lifecycle_defers_updates_to_single_update_only_step(tmp_path):
    steps = _build_steps(
        "2026-07-20", str(tmp_path), True, False,
        defer_scorecard=True, defer_position_update=True,
    )
    simulator = next(step for step in steps if step["name"] == "run_paper_position_simulator")
    assert "--entry-only" in simulator["cmd"]
    assert "--update-with-klines" in simulator["cmd"]


def test_two_same_exposure_intents_in_one_batch_create_only_one():
    second = _intent(
        intent_id="TI_SECOND",
        signal_bar_close_time="2026-07-20T02:00:00+00:00",
        entry_price=101.0,
    )
    result = simulate_intent_only([_intent(), second], "2026-07-20")
    assert result.lifecycle_stats["new_positions_count"] == 1
    assert result.lifecycle_stats["positions_skipped_overlap_open"] == 1


def test_closed_position_allows_later_distinct_signal():
    old = _position(
        "P_OLD", "2026-07-19T00:00:00+00:00", "TAKE_PROFIT_HIT",
        closed_at="2026-07-19T03:00:00+00:00", exit_price=110.0,
    )
    result = simulate_intent_only([_intent()], "2026-07-20", [old])
    assert result.lifecycle_stats["new_positions_count"] == 1


@pytest.mark.parametrize("field,value", [
    ("strategy_id", "other"), ("symbol", "ETHUSDT"),
    ("timeframe", "15m"), ("side", "SHORT"),
])
def test_different_exposure_dimension_is_allowed(field, value):
    old = _position("P_OLD", "2026-07-19T00:00:00+00:00")
    candidate = _intent(**{field: value})
    if field == "side":
        candidate.update(stop_loss=105.0, take_profit=90.0)
    result = simulate_intent_only([candidate], "2026-07-20", [old])
    assert result.lifecycle_stats["new_positions_count"] == 1


def test_stable_signal_key_ignores_random_intent_and_processing_time():
    first = _intent(intent_id="TI_A", created_at="2026-07-20T01:01:01Z")
    second = _intent(intent_id="TI_B", created_at="2026-07-20T01:59:59Z")
    assert stable_signal_key(first) == stable_signal_key(second)
    assert len(stable_signal_key(first)) == 64
    assert exposure_identity(first).endswith("macd_rebound_watch|BTCUSDT|1h|LONG")


def test_legacy_signal_key_is_stable_without_bar_timestamp():
    first = _intent(intent_id="TI_A", signal_bar_close_time=None)
    second = _intent(intent_id="TI_B", signal_bar_close_time=None)
    assert stable_signal_key(first) == stable_signal_key(second)


def test_malformed_ledger_fails_closed(tmp_path):
    (tmp_path / "2026-07-19_paper_position_ledger.jsonl").write_text("{bad json\n")
    with pytest.raises(RuntimeError, match="corrupted_lines=1"):
        _load_entry_guard_state(str(tmp_path), "2026-07-20")


def test_terminal_conflict_fails_closed(tmp_path):
    first = _position(
        "P1", "2026-07-19T00:00:00+00:00", "TAKE_PROFIT_HIT",
        closed_at="2026-07-19T01:00:00+00:00", exit_price=110.0,
    )
    conflict = dict(first, status="STOP_LOSS_HIT", exit_price=95.0,
                    recorded_at="2026-07-19T02:00:00+00:00")
    _write_ledger(tmp_path / "2026-07-19_paper_position_ledger.jsonl", [first, conflict])
    with pytest.raises(RuntimeError, match="terminal_conflict"):
        _load_entry_guard_state(str(tmp_path), "2026-07-20")


def test_duplicate_and_out_of_order_open_state_selects_canonical(tmp_path):
    newer = _position("P1", "2026-07-19T00:00:00+00:00",
                      recorded_at="2026-07-19T03:00:00+00:00", marker="new")
    older = dict(newer, recorded_at="2026-07-19T01:00:00+00:00", marker="old")
    _write_ledger(tmp_path / "2026-07-19_paper_position_ledger.jsonl", [newer, older, newer])
    opens, _all, _keys, _diag = _load_entry_guard_state(str(tmp_path), "2026-07-20")
    assert len(opens) == 1
    assert opens[0]["marker"] == "new"


def test_overlap_manifest_marks_later_position_without_mutating_ledger(tmp_path):
    first = _position(
        "P1", "2026-07-19T00:00:00+00:00", "TAKE_PROFIT_HIT",
        closed_at="2026-07-19T04:00:00+00:00", exit_price=110.0,
    )
    overlap = _position(
        "P2", "2026-07-19T02:00:00+00:00", "STOP_LOSS_HIT",
        closed_at="2026-07-19T03:00:00+00:00", exit_price=95.0,
    )
    later = _position(
        "P3", "2026-07-19T05:00:00+00:00", "TAKE_PROFIT_HIT",
        closed_at="2026-07-19T06:00:00+00:00", exit_price=110.0,
    )
    before = json.dumps([first, overlap, later], sort_keys=True)
    manifest = build_overlap_exclusion_manifest(
        [first, overlap, later], "2026-07-20T00:00:00+00:00",
    )
    assert [item["position_id"] for item in manifest["exclusions"]] == ["P2"]
    assert manifest["exclusions"][0]["overlaps_with_position_id"] == "P1"
    assert json.dumps([first, overlap, later], sort_keys=True) == before
    assert OVERLAP_MANIFEST_FILENAME == "paper_position_overlap_exclusions.json"


def test_scorecard_loader_preserves_raw_count_and_excludes_manifest_overlap(tmp_path):
    first = _position(
        "P1", "2026-07-19T00:00:00+00:00", "TAKE_PROFIT_HIT",
        closed_at="2026-07-19T04:00:00+00:00", exit_price=110.0,
        r_multiple=2.0, quarantine_status="CLEAN",
    )
    overlap = _position(
        "P2", "2026-07-19T02:00:00+00:00", "STOP_LOSS_HIT",
        closed_at="2026-07-19T03:00:00+00:00", exit_price=95.0,
        r_multiple=-1.0, quarantine_status="CLEAN",
    )
    later = _position(
        "P3", "2026-07-19T05:00:00+00:00", "TAKE_PROFIT_HIT",
        closed_at="2026-07-19T06:00:00+00:00", exit_price=110.0,
        r_multiple=2.0, quarantine_status="CLEAN",
    )
    records = [first, overlap, later]
    _write_ledger(tmp_path / "2026-07-19_paper_position_ledger.jsonl", records)
    (tmp_path / "2026-07-19_shadow_lifecycle_result.json").write_text(json.dumps({
        "date": "2026-07-19",
        "mode": "real_public_readonly",
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }))
    manifest = build_overlap_exclusion_manifest(
        records, "2026-07-20T00:00:00+00:00",
    )
    (tmp_path / OVERLAP_MANIFEST_FILENAME).write_text(json.dumps(manifest))

    eligible, _all, diag = load_canonical_closed_clean_positions(str(tmp_path))

    assert diag["raw_canonical_closed"] == 3
    assert diag["excluded_overlap_closed"] == 1
    assert diag["eligible_legacy_closed"] == 2
    assert diag["trusted_cohort_closed"] == 0
    assert {position["position_id"] for position in eligible} == {"P1", "P3"}
